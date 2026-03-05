# 💰 FinFlow — Sistema de Controle Financeiro

Sistema de controle financeiro multi-usuário, responsivo, construído com Flask + SQLAlchemy + PostgreSQL + Docker.

## 🚀 Tecnologias

- **Backend**: Flask (MVC), SQLAlchemy ORM, Flask-Migrate, Flask-Login
- **Banco de dados**: PostgreSQL 15
- **Infraestrutura**: Docker + Docker Compose
- **Frontend**: HTML/CSS/JS puro, responsivo, Chart.js, Lucide Icons

---

## ⚡ Como rodar com Docker (recomendado)

### Pré-requisitos
- Docker
- Docker Compose

### 1. Suba os containers

```bash
docker-compose up --build -d
```

### 2. Acesse o sistema

Abra no navegador: **http://localhost:5000**

Crie sua conta em `/auth/register`.

---

## 🛠 Como rodar localmente (sem Docker)

### Pré-requisitos
- Python 3.11+
- PostgreSQL rodando localmente

### 1. Instale as dependências

```bash
pip install -r requirements.txt
```

### 2. Configure o .env

Edite `.env` com sua conexão PostgreSQL:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/finflow
SECRET_KEY=sua-chave-secreta
```

### 3. Crie o banco e rode as migrations

```bash
flask db init
flask db migrate -m "Initial"
flask db upgrade
```

### 4. Rode o servidor

```bash
python run.py
```

---

## 📂 Estrutura MVC

```
finflow/
├── app/
│   ├── controllers/          # Rotas e lógica de negócio (Controller)
│   │   ├── auth_controller.py
│   │   ├── dashboard_controller.py
│   │   ├── transaction_controller.py
│   │   ├── category_controller.py
│   │   ├── account_controller.py
│   │   └── report_controller.py
│   ├── models/               # Entidades do banco (Model)
│   │   ├── user.py
│   │   ├── account.py
│   │   ├── category.py
│   │   └── transaction.py
│   └── views/templates/      # Templates HTML (View)
│       ├── base.html
│       ├── auth/
│       └── dashboard/
├── config.py
├── run.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## ✅ Funcionalidades

- **Multi-usuário** com autenticação segura (bcrypt)
- **Dashboard** com saldo atual, receitas, despesas, atrasados
- **Lançamentos** (débito/crédito) com:
  - Categorização
  - Multi-contas
  - Recorrência (semanal, mensal, anual...)
  - Parcelamento
  - Marcação de pago/pendente
- **Transferências** entre contas
- **Análises**: gráfico de fluxo anual, distribuição por categoria
- **Pendências**: vencidos e próximos vencimentos
- **Gerenciamento** de categorias e contas bancárias
- **Notificações** in-app
- **Responsivo** — funciona perfeitamente no celular

---

## 🔒 Segurança

- Senhas hasheadas com Werkzeug (bcrypt)
- Sessões seguras com Flask-Login
- Cada usuário vê apenas seus próprios dados
- CSRF protection com Flask-WTF

---

## 📱 Responsividade

Layout adaptável para desktop, tablet e celular com sidebar deslizante.
