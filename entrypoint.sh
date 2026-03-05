#!/bin/bash
set -e

# DATABASE_URL usa postgresql+psycopg:// para o SQLAlchemy
# Para psycopg.connect() precisamos da URL sem o +psycopg
PSYCOPG_URL="${DATABASE_URL/postgresql+psycopg:\/\//postgresql://}"

echo "⏳ Aguardando PostgreSQL..."
python -c "
import time, psycopg, os
url = '${PSYCOPG_URL}'
for i in range(30):
    try:
        psycopg.connect(url)
        print('✅ PostgreSQL pronto!')
        break
    except Exception as e:
        print(f'Tentativa {i+1}/30... ({e})')
        time.sleep(2)
"

echo "📦 Inicializando migrações..."
if [ ! -d "migrations" ]; then
    flask db init
fi

echo "🔄 Gerando migração..."
flask db migrate -m "init" 2>/dev/null || true

echo "⬆️ Aplicando migrações..."
flask db upgrade 2>/tmp/migrate_err.txt || {
    echo "⚠️  Conflito de revisão detectado, resetando histórico Alembic..."
    python -c "
import psycopg, os
url = '${PSYCOPG_URL}'
conn = psycopg.connect(url)
cur = conn.cursor()
cur.execute('DROP TABLE IF EXISTS alembic_version;')
conn.commit()
conn.close()
print('✅ Tabela alembic_version removida.')
"
    flask db upgrade
}

echo "🔧 Garantindo tabelas extras..."
python -c "
from app import create_app, db
import app.models
app = create_app()
with app.app_context():
    db.create_all()
    print('✅ Tabelas verificadas/criadas.')
"

echo "🔧 Garantindo colunas novas (role, plan_status, etc.)..."
python -c "
import psycopg, os
url = '${PSYCOPG_URL}'
conn = psycopg.connect(url)
cur = conn.cursor()

# Users: role, plan_status, plan_expires_at
cols = [
    (\"users\", \"role\",           \"VARCHAR(20) DEFAULT 'prata'\"),
    (\"users\", \"plan_status\",    \"VARCHAR(20) DEFAULT 'trial'\"),
    (\"users\", \"plan_expires_at\",\"TIMESTAMP\"),
    # Accounts: closing_day, due_day
    (\"accounts\", \"closing_day\", \"INTEGER\"),
    (\"accounts\", \"due_day\",      \"INTEGER\"),
]
for table, col, coltype in cols:
    cur.execute(f\"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND column_name='{col}'\")
    if not cur.fetchone():
        cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {coltype}')
        print(f'  ✅ Coluna {table}.{col} criada.')
    else:
        print(f'  ✓  Coluna {table}.{col} já existe.')

conn.commit()
conn.close()
"

echo "🌱 Seed inicial..."
python seed.py

echo "🚀 Iniciando servidor..."
exec gunicorn -w 2 -b 0.0.0.0:5000 "wsgi:app"
