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

echo "🏗️  Criando/atualizando tabelas..."
python -c "
from app import create_app, db
import app.models
application = create_app()
with application.app_context():
    db.create_all()
    print('  ✅ db.create_all() concluido.')
"

echo "🔧 Garantindo colunas novas..."
python -c "
import psycopg, os
url = '${PSYCOPG_URL}'
conn = psycopg.connect(url)
cur = conn.cursor()

new_cols = [
    ('users',    'role',             \"VARCHAR(20) DEFAULT 'prata'\"),
    ('users',    'plan_status',      \"VARCHAR(20) DEFAULT 'trial'\"),
    ('users',    'plan_expires_at',  'TIMESTAMP'),
    ('accounts', 'closing_day',      'INTEGER'),
    ('accounts', 'due_day',          'INTEGER'),
    ('budgets',  'recurrence',       'INTEGER DEFAULT 0'),
    ('budgets',  'recurrence_group', 'VARCHAR(36)'),
]

for table, col, coldef in new_cols:
    cur.execute(
        \"SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s\",
        (table, col)
    )
    if not cur.fetchone():
        cur.execute(f'ALTER TABLE {table} ADD COLUMN {col} {coldef}')
        print(f'  ✅ {table}.{col} adicionada.')
    else:
        print(f'  ✓  {table}.{col} ja existe.')

conn.commit()
conn.close()
print('  ✅ Schema atualizado.')
"

echo "🌱 Seed inicial..."
python seed.py

echo "🚀 Iniciando servidor..."
exec gunicorn -w 2 -b 0.0.0.0:5000 "wsgi:app"