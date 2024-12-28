# 🎲 Painel Webloto - Sistema de Gestão de Contribuições

## 📋 Sobre o Projeto

Painel Webloto é uma aplicação web desenvolvida para gerenciar contribuições mensais de um grupo de pessoas que participam de apostas coletivas em loterias. O sistema oferece uma interface intuitiva para cadastro de contribuintes, registro de pagamentos e acompanhamento de contribuições mensais.

## 🚀 Funcionalidades

### 👥 Gestão de Usuários
- Cadastro de contribuintes com informações pessoais
- Visualização e edição de dados cadastrais
- Interface dedicada para gerenciamento de usuários

### 💰 Controle de Contribuições
- Registro mensal de contribuições
- Status de pagamento (Pendente/Pago)
- Confirmação de pagamentos com modal de verificação
- Exclusão de registros com confirmação

### 📊 Dashboard
- Total arrecadado no mês
- Total esperado no mês
- Total arrecadado no ano
- Total esperado no ano

## 🛠️ Tecnologias Utilizadas

### Backend
- **Flask** (v3.1.0): Framework web em Python, escolhido pela sua simplicidade e flexibilidade
- **SQLAlchemy** (v2.0.36): ORM para interação com banco de dados
- **Flask-SQLAlchemy** (v3.1.1): Integração do SQLAlchemy com Flask

### Frontend
- **Bootstrap 5**: Framework CSS para design responsivo
- **Bootstrap Icons**: Biblioteca de ícones
- **JavaScript**: Interatividade e validações do lado do cliente

### Banco de Dados
- **SQLite**: Banco de dados relacional leve e sem necessidade de servidor

## 📦 Dependências

```txt
blinker==1.9.0
click==8.1.8
Flask==3.1.0
Flask-SQLAlchemy==3.1.1
greenlet==3.1.1
itsdangerous==2.2.0
Jinja2==3.1.3
MarkupSafe==3.0.2
SQLAlchemy==2.0.36
typing_extensions==4.12.2
Werkzeug==3.1.3
```

## 🚀 Como Executar

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/lotoamizade.git
cd lotoamizade
```

2. Crie um ambiente virtual e ative-o:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Execute a aplicação:
```bash
python app.py
```

5. Acesse no navegador:
```
http://localhost:5000
```

## 🎯 Fluxo de Uso

1. **Cadastro de Usuários**
   - Acesse "Adicionar Contribuinte" no menu
   - Preencha os dados pessoais
   - Os usuários cadastrados ficam disponíveis na página "Usuários"

2. **Registro de Contribuições**
   - Use o botão "Inserir Contribuinte" na página principal
   - Selecione o usuário e defina o valor
   - O contribuinte aparece na lista com status "Pendente"

3. **Confirmação de Pagamentos**
   - Clique no botão ✓ para confirmar um pagamento
   - Verifique os dados no modal de confirmação
   - Após confirmar, o status muda para "Pago"

## 👤 Author

Leo Gama
- GitHub: [@LeoGamaJ](https://github.com/LeoGamaJ)
- Email: leo@leogama.cloud 
- LinkedIn: (https://www.linkedin.com/in/leonardo-gama-jardim/)

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE]

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir uma issue ou enviar um pull request.
