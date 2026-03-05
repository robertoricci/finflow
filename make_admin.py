
import os
from app import create_app, db
from app.models import User
import bcrypt

app = create_app()

with app.app_context():

    name = os.getenv("ADMIN_NAME")
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")

    if not email or not password:
        print("Variáveis ADMIN não definidas")
        exit()

    user = User.query.filter_by(email=email).first()

    if user:
        print("Admin já existe.")
    else:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        admin = User(
            name=name,
            email=email,
            password=hashed,
            is_admin=True,
            plan_status = 'active'
        )

        db.session.add(admin)
        db.session.commit()

        print("Admin criado com sucesso!")
