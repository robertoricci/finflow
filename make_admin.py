"""
Rode com: docker compose exec web python make_admin.py EMAIL
Promove um usuário existente a admin.
"""
import sys
from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    email = sys.argv[1] if len(sys.argv) > 1 else None
    if not email:
        # Se não passou email, promove o primeiro usuário cadastrado
        u = User.query.order_by(User.id).first()
    else:
        u = User.query.filter_by(email=email).first()

    if not u:
        print('Usuário não encontrado.')
        sys.exit(1)

    u.role = 'admin'
    u.plan_status = 'active'
    db.session.commit()
    print(f'✅ {u.name} ({u.email}) agora é ADMIN.')
