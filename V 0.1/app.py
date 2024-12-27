from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

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
    contribuintes = Contribuinte.query.all()
    mes_atual = datetime.now().strftime('%Y-%m')
    ano_atual = datetime.now().year
    
    # Criar dicionário de status de pagamento e calcular totais
    status_dict = {}
    total_arrecadado_mes = 0
    total_esperado_mes = 0
    total_arrecadado_ano = 0
    total_esperado_ano = 0
    
    for contribuinte in contribuintes:
        if contribuinte.ativo:
            # Buscar contribuição do mês atual
            contribuicao = Contribuicao.query.filter_by(
                contribuinte_id=contribuinte.id,
                mes_referencia=mes_atual
            ).first()
            
            if contribuicao:
                # Totais esperados baseados na contribuição
                total_esperado_mes += contribuicao.valor
                total_esperado_ano += contribuicao.valor * 12
                
                # Status e total arrecadado
                status_dict[contribuinte.id] = contribuicao.status
                if contribuicao.status == 'Pago':
                    total_arrecadado_mes += contribuicao.valor
            else:
                status_dict[contribuinte.id] = 'Não Inserido'
            
            # Somar contribuições pagas do ano
            contribuicoes_ano = Contribuicao.query.filter(
                Contribuicao.contribuinte_id == contribuinte.id,
                Contribuicao.mes_referencia.startswith(str(ano_atual)),
                Contribuicao.status == 'Pago'
            ).all()
            total_arrecadado_ano += sum(c.valor for c in contribuicoes_ano)
    
    return render_template('index.html',
                         contribuintes=contribuintes,
                         status_dict=status_dict,
                         total_arrecadado_mes=total_arrecadado_mes,
                         total_esperado_mes=total_esperado_mes,
                         total_arrecadado_ano=total_arrecadado_ano,
                         total_esperado_ano=total_esperado_ano,
                         mes_atual=mes_atual)

@app.route('/usuarios')
def usuarios():
    usuarios = Contribuinte.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/adicionar', methods=['GET', 'POST'])
def adicionar():
    if request.method == 'POST':
        try:
            nome = request.form['nome']
            email = request.form['email']
            telefone = request.form['telefone']

            # Verificar se o email já existe
            if Contribuinte.query.filter_by(email=email).first():
                flash('Este e-mail já está cadastrado.', 'error')
                return render_template('adicionar.html')

            novo_contribuinte = Contribuinte(
                nome=nome,
                email=email,
                telefone=telefone
            )
            
            db.session.add(novo_contribuinte)
            db.session.commit()
            flash('Contribuinte adicionado com sucesso!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao adicionar contribuinte: {str(e)}', 'error')
            return render_template('adicionar.html')
    
    return render_template('adicionar.html')

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
            contribuinte.ativo = 'ativo' in request.form
            
            # Verificar se o novo email já existe para outro contribuinte
            existente = Contribuinte.query.filter(
                Contribuinte.email == request.form['email'],
                Contribuinte.id != id
            ).first()
            if existente:
                flash('Este e-mail já está cadastrado para outro contribuinte.', 'error')
                return render_template('atualizar.html', contribuinte=contribuinte)
            
            db.session.commit()
            flash('Contribuinte atualizado com sucesso!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar contribuinte: {str(e)}', 'error')
            return render_template('atualizar.html', contribuinte=contribuinte)
    
    return render_template('atualizar.html', contribuinte=contribuinte)

@app.route('/excluir/<int:id>')
def excluir(id):
    try:
        contribuinte = Contribuinte.query.get_or_404(id)
        db.session.delete(contribuinte)
        db.session.commit()
        flash('Contribuinte excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir contribuinte: {str(e)}', 'error')
    return redirect(url_for('index'))

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

if __name__ == '__main__':
    app.run(debug=True)
