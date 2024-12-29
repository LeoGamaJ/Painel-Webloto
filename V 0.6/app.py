from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from collections import defaultdict
import calendar
import os
import pdfkit
import markdown
import io
import re
from sqlalchemy import func, case

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bolao.db'
db = SQLAlchemy(app)

class Contribuinte(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)
    valor_mensal = db.Column(db.Float, default=0.0)  # Valor mensal comprometido
    contribuicoes = db.relationship('Contribuicao', backref='contribuinte', lazy=True)

class Contribuicao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contribuinte_id = db.Column(db.Integer, db.ForeignKey('contribuinte.id'), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_pagamento = db.Column(db.DateTime, default=datetime.utcnow)
    mes_referencia = db.Column(db.String(7), nullable=False)  # Formato: YYYY-MM
    status = db.Column(db.String(20), default='Pendente')  # Pendente, Pago

with app.app_context():
    db.drop_all()  # Excluir todas as tabelas existentes
    db.create_all()  # Criar novas tabelas

@app.route('/')
def index():
    contribuintes = Contribuinte.query.filter_by(ativo=True).all()
    mes_atual = datetime.now()
    mes_atual_str = mes_atual.strftime('%Y-%m')
    
    # Obtém as contribuições do mês atual
    contribuicoes_mes = Contribuicao.query.filter_by(
        mes_referencia=mes_atual_str
    ).all()
    
    # Calcula o total arrecadado no mês (apenas contribuições pagas)
    total_arrecadado_mes = sum(
        c.valor for c in contribuicoes_mes if c.status == 'Pago'
    )
    
    # Calcula o total esperado no mês (soma dos valores mensais dos contribuintes ativos)
    total_esperado_mes = sum(c.valor_mensal for c in contribuintes)
    
    # Obtém todas as contribuições do ano atual
    contribuicoes_ano = Contribuicao.query.filter(
        Contribuicao.mes_referencia.like(f'{mes_atual.year}%')
    ).all()
    
    # Calcula o total arrecadado no ano (apenas contribuições pagas)
    total_arrecadado_ano = sum(
        c.valor for c in contribuicoes_ano if c.status == 'Pago'
    )
    
    # O total esperado do ano é o total mensal multiplicado por 12
    total_esperado_ano = total_esperado_mes * 12
    
    # Obtém os meses únicos para o filtro
    meses_disponiveis = db.session.query(
        db.func.distinct(Contribuicao.mes_referencia)
    ).order_by(
        Contribuicao.mes_referencia.desc()
    ).all()
    
    # Formata os meses para exibição
    meses_formatados = []
    for mes in meses_disponiveis:
        try:
            data = datetime.strptime(mes[0], '%Y-%m')
            meses_formatados.append({
                'valor': mes[0],
                'data': data
            })
        except (ValueError, TypeError):
            continue
    
    # Se não houver meses, inclui o mês atual
    if not meses_formatados:
        meses_formatados = [{
            'valor': mes_atual_str,
            'data': mes_atual
        }]
    
    # Prepara as estatísticas para os cards
    estatisticas = {
        'total_arrecadado_mes': total_arrecadado_mes,
        'total_esperado_mes': total_esperado_mes,
        'total_arrecadado_ano': total_arrecadado_ano,
        'total_esperado_ano': total_esperado_ano,
        'qtd_pagos_mes': len([c for c in contribuicoes_mes if c.status == 'Pago']),
        'qtd_pendentes_mes': len([c for c in contribuicoes_mes if c.status == 'Pendente'])
    }
    
    return render_template('index.html',
                         contribuintes=contribuintes,
                         mes_atual=mes_atual,
                         mes_atual_str=mes_atual_str,
                         meses_disponiveis=meses_formatados,
                         estatisticas=estatisticas)

@app.route('/usuarios')
def usuarios():
    usuarios = Contribuinte.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/adicionar', methods=['POST'])
def adicionar():
    try:
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        
        # Converte o valor monetário formatado para float
        valor_str = request.form.get('valor_mensal', '0,00')
        valor_str = valor_str.replace('.', '').replace(',', '.')
        valor_mensal = float(valor_str)

        # Verificar se o email já existe
        if Contribuinte.query.filter_by(email=email).first():
            flash('Este e-mail já está cadastrado. Por favor, use um e-mail diferente.', 'error')
            return redirect(url_for('usuarios'))

        novo_contribuinte = Contribuinte(
            nome=nome,
            email=email,
            telefone=telefone,
            valor_mensal=valor_mensal
        )
        
        db.session.add(novo_contribuinte)
        db.session.commit()
        flash(f'Usuário {nome} foi adicionado com sucesso!', 'success')
        return redirect(url_for('usuarios'))
    except ValueError:
        flash('O valor mensal informado é inválido. Use apenas números e vírgula.', 'error')
        return redirect(url_for('usuarios'))
    except Exception as e:
        flash('Ocorreu um erro ao adicionar o usuário. Verifique os dados e tente novamente.', 'error')
        return redirect(url_for('usuarios'))

@app.route('/inserir_contribuicao', methods=['GET', 'POST'])
def inserir_contribuicao():
    if request.method == 'GET':
        contribuinte_id = request.args.get('contribuinte')
        contribuintes = Contribuinte.query.filter_by(ativo=True).all()
        contribuinte_selecionado = None
        if contribuinte_id:
            contribuinte_selecionado = Contribuinte.query.get(contribuinte_id)
        return render_template('inserir_contribuicao.html', 
                            contribuintes=contribuintes,
                            contribuinte_selecionado=contribuinte_selecionado,
                            now=datetime.now())
    
    try:
        contribuinte_id = request.form['contribuinte_id']
        valor = float(request.form['valor'])
        mes_referencia = request.form['mes_referencia']
        
        # Verificar se já existe contribuição para este mês
        contribuicao_existente = Contribuicao.query.filter_by(
            contribuinte_id=contribuinte_id,
            mes_referencia=mes_referencia
        ).first()
        
        if contribuicao_existente:
            flash('Este contribuinte já foi inserido para este mês.', 'error')
            return redirect(url_for('inserir_contribuicao'))
        
        nova_contribuicao = Contribuicao(
            contribuinte_id=contribuinte_id,
            valor=valor,
            mes_referencia=mes_referencia,
            status='Pendente'
        )
        
        db.session.add(nova_contribuicao)
        db.session.commit()
        flash('Contribuinte inserido com sucesso!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao inserir contribuinte: {str(e)}', 'error')
        return redirect(url_for('inserir_contribuicao'))

@app.route('/registrar_pagamento/<int:contribuicao_id>')
def registrar_pagamento(contribuicao_id):
    try:
        contribuicao = Contribuicao.query.get_or_404(contribuicao_id)
        contribuicao.status = 'Pago'
        contribuicao.data_pagamento = datetime.utcnow()
        db.session.commit()
        flash('Pagamento registrado com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar pagamento: {str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/atualizar/<int:id>', methods=['GET', 'POST'])
def atualizar(id):
    contribuinte = Contribuinte.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            contribuinte.nome = request.form['nome']
            contribuinte.email = request.form['email']
            contribuinte.telefone = request.form['telefone']
            
            # Converte o valor monetário formatado para float
            valor_str = request.form.get('valor_mensal', '0,00')
            valor_str = valor_str.replace('.', '').replace(',', '.')
            contribuinte.valor_mensal = float(valor_str)
            
            contribuinte.ativo = 'ativo' in request.form
            
            # Verificar se o email já existe e não é do usuário atual
            email_existente = Contribuinte.query.filter(
                Contribuinte.email == request.form['email'],
                Contribuinte.id != id
            ).first()
            
            if email_existente:
                flash('Este e-mail já está sendo usado por outro usuário. Por favor, escolha outro e-mail.', 'error')
                return render_template('atualizar.html', contribuinte=contribuinte)
            
            db.session.commit()
            flash(f'As informações de {contribuinte.nome} foram atualizadas com sucesso!', 'success')
            return redirect(url_for('usuarios'))
        except ValueError:
            flash('O valor mensal informado é inválido. Use apenas números e vírgula.', 'error')
            return render_template('atualizar.html', contribuinte=contribuinte)
        except Exception as e:
            db.session.rollback()
            flash('Ocorreu um erro ao atualizar o usuário. Verifique os dados e tente novamente.', 'error')
            return render_template('atualizar.html', contribuinte=contribuinte)
    
    return render_template('atualizar.html', contribuinte=contribuinte)

@app.route('/excluir/<int:id>')
def excluir(id):
    try:
        contribuinte = Contribuinte.query.get_or_404(id)
        nome = contribuinte.nome
        db.session.delete(contribuinte)
        db.session.commit()
        flash(f'O usuário {nome} foi excluído com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Ocorreu um erro ao excluir o usuário. Por favor, tente novamente.', 'error')
    return redirect(url_for('usuarios'))

@app.route('/excluir_contribuicao/<int:id>')
def excluir_contribuicao(id):
    try:
        contribuicao = Contribuicao.query.get_or_404(id)
        db.session.delete(contribuicao)
        db.session.commit()
        flash('Contribuição excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir contribuição: {str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/analises')
def analises():
    # Obtém o momento atual
    hoje = datetime.now()
    momento_atual = hoje.strftime('%d/%m/%Y às %H:%M')
    mes_atual = hoje.strftime('%Y-%m')
    
    # Dados para o gráfico de contribuições mensais (últimos 6 meses)
    labels_contribuicoes = []
    valores_contribuicoes = []
    valores_inadimplencia = []
    labels_inadimplencia = []
    
    for i in range(5, -1, -1):
        data = hoje - timedelta(days=i*30)
        mes_ref = data.strftime('%Y-%m')
        nome_mes = data.strftime('%b/%y')
        labels_contribuicoes.append(nome_mes)
        labels_inadimplencia.append(nome_mes)
        
        # Total de contribuições
        contribuicoes_mes = Contribuicao.query.filter_by(
            mes_referencia=mes_ref,
            status='Pago'
        ).all()
        
        total_contribuicoes = sum(c.valor for c in contribuicoes_mes)
        valores_contribuicoes.append(total_contribuicoes)
        
        # Taxa de inadimplência
        total_contribuintes = Contribuinte.query.filter_by(ativo=True).count()
        pagamentos_em_dia = Contribuicao.query.filter_by(
            mes_referencia=mes_ref,
            status='Pago'
        ).count()
        
        taxa = ((total_contribuintes - pagamentos_em_dia) / total_contribuintes * 100) if total_contribuintes > 0 else 0
        valores_inadimplencia.append(round(taxa, 1))

    # Dados para o gráfico de status do mês atual
    contribuicoes_mes_atual = Contribuicao.query.filter_by(mes_referencia=mes_atual).all()
    contribuintes_em_dia = sum(1 for c in contribuicoes_mes_atual if c.status == 'Pago')
    contribuintes_atrasados = sum(1 for c in contribuicoes_mes_atual if c.status == 'Pendente')
    contribuintes_pendentes = len(contribuicoes_mes_atual) - contribuintes_em_dia - contribuintes_atrasados

    # Cálculo da média de atraso
    contribuicoes_atrasadas = []
    todas_contribuicoes = Contribuicao.query.filter_by(status='Pago').all()
    
    for contribuicao in todas_contribuicoes:
        try:
            data_ref = datetime.strptime(contribuicao.mes_referencia + '-01', '%Y-%m-%d')
            ultimo_dia = calendar.monthrange(data_ref.year, data_ref.month)[1]
            data_limite = datetime(data_ref.year, data_ref.month, ultimo_dia)
            
            if contribuicao.data_pagamento and contribuicao.data_pagamento > data_limite:
                dias_atraso = (contribuicao.data_pagamento - data_limite).days
                contribuicoes_atrasadas.append(dias_atraso)
        except (ValueError, TypeError):
            continue
    
    media_atraso = round(sum(contribuicoes_atrasadas) / len(contribuicoes_atrasadas)) if contribuicoes_atrasadas else 0

    # Cálculo da estimativa de arrecadação
    valor_medio_ultimos_meses = sum(valores_contribuicoes) / len(valores_contribuicoes) if valores_contribuicoes else 0
    taxa_crescimento = ((valores_contribuicoes[-1] / valores_contribuicoes[0]) - 1) if valores_contribuicoes and valores_contribuicoes[0] != 0 else 0
    estimativa_arrecadacao = valor_medio_ultimos_meses * (1 + taxa_crescimento)

    # Percentual da estimativa em relação à meta
    meta = max(valores_contribuicoes) if valores_contribuicoes else 0
    percentual_estimativa = min(round((estimativa_arrecadacao / meta * 100) if meta > 0 else 0), 100)

    # Taxa de inadimplência atual
    taxa_inadimplencia = valores_inadimplencia[-1] if valores_inadimplencia else 0

    # Identificação de contribuintes com padrão de atraso
    alertas_atraso = []
    contribuintes = Contribuinte.query.filter_by(ativo=True).all()
    
    for contribuinte in contribuintes:
        contribuicoes = Contribuicao.query.filter_by(
            contribuinte_id=contribuinte.id,
            status='Pago'
        ).order_by(Contribuicao.mes_referencia.desc()).limit(6).all()
        
        total_atrasos = 0
        for c in contribuicoes:
            try:
                data_ref = datetime.strptime(c.mes_referencia + '-01', '%Y-%m-%d')
                ultimo_dia = calendar.monthrange(data_ref.year, data_ref.month)[1]
                data_limite = datetime(data_ref.year, data_ref.month, ultimo_dia)
                
                if c.data_pagamento and c.data_pagamento > data_limite:
                    total_atrasos += 1
            except (ValueError, TypeError):
                continue

        if total_atrasos >= 2 and len(contribuicoes) >= 3:  # Se atrasou pelo menos 2 vezes nos últimos 6 meses
            probabilidade = (total_atrasos / len(contribuicoes)) * 100
            alertas_atraso.append({
                'nome': contribuinte.nome,
                'meses_atraso': total_atrasos,
                'probabilidade': round(probabilidade)
            })
    
    # Ordena alertas por probabilidade de atraso (descendente)
    alertas_atraso.sort(key=lambda x: x['probabilidade'], reverse=True)

    return render_template('analises.html',
                         labels_contribuicoes=labels_contribuicoes,
                         valores_contribuicoes=valores_contribuicoes,
                         contribuintes_em_dia=contribuintes_em_dia,
                         contribuintes_atrasados=contribuintes_atrasados,
                         contribuintes_pendentes=contribuintes_pendentes,
                         media_atraso=media_atraso,
                         taxa_inadimplencia=taxa_inadimplencia,
                         labels_inadimplencia=labels_inadimplencia,
                         valores_inadimplencia=valores_inadimplencia,
                         estimativa_arrecadacao=estimativa_arrecadacao,
                         percentual_estimativa=percentual_estimativa,
                         alertas_atraso=alertas_atraso,
                         momento_atual=momento_atual)

@app.route('/relatorios')
def relatorios():
    contribuintes = Contribuinte.query.all()
    return render_template('relatorios.html', 
                         contribuintes=contribuintes,
                         momento_atual=datetime.now().strftime('%d/%m/%Y %H:%M'))

@app.route('/gerar_relatorio', methods=['POST'])
def gerar_relatorio():
    try:
        tipo_relatorio = request.form.get('tipo')
        formato = request.form.get('formato')
        periodo = request.form.get('periodo')
        contribuinte_id = request.form.get('contribuinte_id')
        
        # Validação dos campos
        if not tipo_relatorio:
            return jsonify({'error': 'Tipo de relatório é obrigatório'}), 400
        if not formato:
            return jsonify({'error': 'Formato de saída é obrigatório'}), 400
        if tipo_relatorio == 'mensal' and not periodo:
            return jsonify({'error': 'Período é obrigatório para relatório mensal'}), 400
        if tipo_relatorio == 'contribuinte' and not contribuinte_id:
            return jsonify({'error': 'Contribuinte é obrigatório para relatório individual'}), 400
        
        # Preparar dados do relatório com timeout
        try:
            dados = preparar_dados_relatorio(tipo_relatorio, periodo, contribuinte_id)
            if not dados:
                return jsonify({'error': 'Não foi possível gerar o relatório com os dados fornecidos'}), 400
                
            dados['momento_atual'] = datetime.now().strftime('%d/%m/%Y %H:%M')
            
            # Gerar conteúdo do relatório
            template_path = f'relatorios/{tipo_relatorio}.html'
            if not os.path.exists(os.path.join(app.template_folder, template_path)):
                return jsonify({'error': f'Template não encontrado: {template_path}'}), 404
                
            conteudo = render_template(template_path, dados=dados)
            
            # Se for visualização HTML, retorna o conteúdo renderizado
            if formato == 'html':
                return jsonify({'conteudo': conteudo})
            
            # Para outros formatos, prepara o download do arquivo
            if formato == 'pdf':
                try:
                    pdf = pdfkit.from_string(
                        conteudo, 
                        False,
                        options={
                            'encoding': 'UTF-8',
                            'page-size': 'A4',
                            'margin-top': '1.0cm',
                            'margin-right': '1.0cm',
                            'margin-bottom': '1.0cm',
                            'margin-left': '1.0cm',
                            'enable-local-file-access': None
                        }
                    )
                    response = make_response(pdf)
                    response.headers['Content-Type'] = 'application/pdf'
                    response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{tipo_relatorio}_{datetime.now().strftime("%Y%m%d")}.pdf'
                    return response
                except Exception as e:
                    app.logger.error(f'Erro ao gerar PDF: {str(e)}')
                    return jsonify({'error': 'Erro ao gerar PDF. Por favor, tente novamente.'}), 500
            
            # Para outros formatos (md, txt)
            response = make_response(conteudo)
            response.headers['Content-Type'] = 'text/plain'
            response.headers['Content-Disposition'] = f'attachment; filename=relatorio_{tipo_relatorio}_{datetime.now().strftime("%Y%m%d")}.{formato}'
            return response
            
        except Exception as e:
            app.logger.error(f'Erro ao preparar dados do relatório: {str(e)}')
            return jsonify({'error': 'Erro ao preparar dados do relatório. Por favor, tente novamente.'}), 500
            
    except Exception as e:
        app.logger.error(f'Erro ao gerar relatório: {str(e)}')
        return jsonify({'error': 'Erro interno do servidor. Por favor, tente novamente.'}), 500

def preparar_dados_relatorio(tipo, periodo=None, contribuinte_id=None):
    try:
        dados = {}
        
        if tipo == 'geral':
            dados['contribuintes'] = Contribuinte.query.all()
            if not dados['contribuintes']:
                return None
                
            dados['total_arrecadado'] = db.session.query(
                func.sum(Contribuicao.valor)
            ).filter(
                Contribuicao.status == 'Pago'
            ).scalar() or 0
            
        elif tipo == 'mensal':
            try:
                mes_ref = datetime.strptime(periodo, '%Y-%m')
                dados['periodo'] = mes_ref.strftime('%B/%Y')
                dados['contribuicoes'] = Contribuicao.query.filter(
                    Contribuicao.mes_referencia == mes_ref.strftime('%Y-%m')
                ).all()
                
                if not dados['contribuicoes']:
                    dados['contribuicoes'] = []  # Retorna lista vazia em vez de None
                
            except ValueError:
                app.logger.error(f'Formato de período inválido: {periodo}')
                return None
            
        elif tipo == 'contribuinte':
            try:
                # Usando Session.get() em vez de Query.get()
                contribuinte = db.session.get(Contribuinte, contribuinte_id)
                if not contribuinte:
                    return None
                    
                dados['contribuinte'] = contribuinte
                dados['contribuicoes'] = sorted(
                    [c for c in contribuinte.contribuicoes],  # Força avaliação da query
                    key=lambda x: datetime.strptime(x.mes_referencia, '%Y-%m'),
                    reverse=True
                )
            except Exception as e:
                app.logger.error(f'Erro ao buscar contribuinte: {str(e)}')
                return None
        
        return dados
        
    except Exception as e:
        app.logger.error(f'Erro ao preparar dados do relatório: {str(e)}')
        return None

if __name__ == '__main__':
    app.run(debug=True)