# #!/bin/bash
# set -e

# echo "Inicializando migrações..."
# if [ ! -d "migrations" ]; then
#     flask db init
# fi

# echo "Gerando migração..."
# flask db migrate -m "init" 2>/dev/null || true

# echo "Aplicando migrações..."
# flask db upgrade 2>/tmp/migrate_err.txt || {
#     echo "Conflito de revisão detectado, resetando..."
#     python -c "
# import psycopg, os
# conn = psycopg.connect(os.environ['DATABASE_URL'])
# conn.autocommit = True
# conn.execute('DROP TABLE IF EXISTS alembic_version;')
# conn.close()
# print('Tabela alembic_version removida.')
# "
#     flask db upgrade
# }

# echo "Make..."
# ##python make_admin.py

# echo "Iniciando servidor..."
# exec gunicorn -w 2 -b 0.0.0.0:$PORT "wsgi:app"


# #!/bin/bash
# set -e

# echo "Inicializando migrações..."
# if [ ! -d "migrations" ]; then
#     flask db init
# fi

# echo "Gerando migração..."
# flask db migrate -m "init" || true

# echo "Aplicando migrações..."
# flask db upgrade || {

#     echo "Conflito alembic detectado..."

#     python <<EOF
# import os
# import psycopg

# url = os.environ["DATABASE_URL"]

# # remover driver do SQLAlchemy
# if url.startswith("postgresql+psycopg://"):
#     url = url.replace("postgresql+psycopg://", "postgresql://", 1)

# if url.startswith("postgres://"):
#     url = url.replace("postgres://", "postgresql://", 1)

# conn = psycopg.connect(url)
# conn.execute("DROP TABLE IF EXISTS alembic_version;")
# conn.close()

# print("Tabela alembic_version removida.")
# EOF

#     flask db upgrade
# }

# echo "🌱 make inicial..."

# python make_admin.py

# echo "Iniciando servidor..."

# exec gunicorn -w 2 -b 0.0.0.0:$PORT wsgi:app



#!/bin/bash
set -e

echo "Inicializando migrações..."
if [ ! -d "migrations" ]; then
    flask db init
fi

echo "Gerando migração..."
flask db migrate -m "init" || true

echo "Aplicando migrações..."
flask db upgrade || {

    echo "Conflito alembic detectado..."

python <<EOF
import os
import psycopg

url = os.environ["DATABASE_URL"]

if url.startswith("postgresql+psycopg://"):
    url = url.replace("postgresql+psycopg://", "postgresql://", 1)

conn = psycopg.connect(url)
conn.execute("DROP TABLE IF EXISTS alembic_version;")
conn.close()

print("Tabela alembic_version removida.")
EOF

    flask db stamp head
    flask db upgrade
}

echo "Criando admin..."
python make_admin.py || true

echo "Iniciando servidor..."
exec gunicorn -w 2 -b 0.0.0.0:$PORT wsgi:app