from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models.user import User
from datetime import datetime

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Acesso negado.'}), 403
        return f(*args, **kwargs)
    return decorated


# ── Página do painel admin (renderiza o dashboard com flag admin) ──
@admin_bp.route('/')
@login_required
def index():
    if not current_user.is_admin:
        return redirect(url_for('dashboard.index'))
    return render_template('admin/index.html')


# ── API: listar usuários ──
@admin_bp.route('/api/users')
@login_required
@admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([_user_dict(u) for u in users])


# ── API: buscar um usuário ──
@admin_bp.route('/api/users/<int:uid>')
@login_required
@admin_required
def get_user(uid):
    u = User.query.get_or_404(uid)
    return jsonify(_user_dict(u))


# ── API: criar usuário ──
@admin_bp.route('/api/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    from app.models.account import Account
    from app.models.category import Category, DEFAULT_CATEGORIES
    from app.models.transaction import Notification

    data = request.get_json()
    name  = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    if not name or not email or not password:
        return jsonify({'error': 'Nome, e-mail e senha são obrigatórios.'}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'E-mail já cadastrado.'}), 400

    expires = None
    if data.get('plan_expires_at'):
        try:
            expires = datetime.strptime(data['plan_expires_at'], '%Y-%m-%d')
        except ValueError:
            pass

    u = User(
        name=name, email=email,
        role=data.get('role', 'prata'),
        plan_status=data.get('plan_status', 'trial'),
        plan_expires_at=expires,
        is_active=bool(data.get('is_active', True)),
    )
    u.set_password(password)
    db.session.add(u)
    db.session.flush()

    db.session.add(Account(user_id=u.id, name='Conta Principal', balance=0.0, color='#1a73e8'))
    for cat in DEFAULT_CATEGORIES:
        db.session.add(Category(user_id=u.id, **cat))
    db.session.add(Notification(user_id=u.id,
        title='Bem-vindo ao FinFlow!',
        message=f'Olá {name}, seja bem-vindo ao FinFlow!'))
    db.session.commit()
    return jsonify({'success': True, 'id': u.id})


# ── API: atualizar usuário ──
@admin_bp.route('/api/users/<int:uid>', methods=['PUT'])
@login_required
@admin_required
def update_user(uid):
    u = User.query.get_or_404(uid)
    data = request.get_json()

    if 'name'  in data: u.name  = data['name'].strip()
    if 'email' in data:
        email = data['email'].strip().lower()
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != uid:
            return jsonify({'error': 'E-mail já está em uso.'}), 400
        u.email = email
    if 'role'        in data: u.role        = data['role']
    if 'plan_status' in data: u.plan_status = data['plan_status']
    if 'is_active'   in data: u.is_active   = bool(data['is_active'])
    if 'plan_expires_at' in data:
        try:
            u.plan_expires_at = datetime.strptime(data['plan_expires_at'], '%Y-%m-%d') if data['plan_expires_at'] else None
        except ValueError:
            pass
    if data.get('password'):
        if len(data['password']) < 6:
            return jsonify({'error': 'Senha deve ter no mínimo 6 caracteres.'}), 400
        u.set_password(data['password'])

    db.session.commit()
    return jsonify({'success': True, 'user': _user_dict(u)})


# ── API: estatísticas gerais ──
@admin_bp.route('/api/stats')
@login_required
@admin_required
def stats():
    from app.models.transaction import Transaction
    from app.models.account import Account

    total_users    = User.query.count()
    active_users   = User.query.filter_by(is_active=True).count()
    inactive_users = total_users - active_users
    by_role = {r: User.query.filter_by(role=r).count() for r in ('admin','ouro','prata','bronze')}
    by_status = {s: User.query.filter_by(plan_status=s).count() for s in ('active','trial','overdue','cancelled')}

    return jsonify({
        'total_users': total_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'by_role': by_role,
        'by_status': by_status,
    })


def _user_dict(u):
    return {
        'id': u.id,
        'name': u.name,
        'email': u.email,
        'role': u.role,
        'role_label': u.plan_label,
        'is_active': u.is_active,
        'plan_status': u.plan_status,
        'plan_status_label': u.plan_status_label,
        'plan_expires_at': u.plan_expires_at.strftime('%Y-%m-%d') if u.plan_expires_at else None,
        'created_at': u.created_at.strftime('%d/%m/%Y') if u.created_at else None,
    }

# ── API: enviar notificação para usuário(s) ──
@admin_bp.route('/api/notify', methods=['POST'])
@login_required
@admin_required
def send_notification():
    from app.models.transaction import Notification
    data = request.get_json()
    title   = data.get('title', '').strip()
    message = data.get('message', '').strip()
    user_ids = data.get('user_ids', [])   # lista de IDs ou 'all'

    if not title or not message:
        return jsonify({'error': 'Título e mensagem são obrigatórios.'}), 400

    if user_ids == 'all' or not user_ids:
        users = User.query.filter_by(is_active=True).all()
    else:
        users = User.query.filter(User.id.in_(user_ids)).all()

    count = 0
    for u in users:
        db.session.add(Notification(
            user_id=u.id,
            title=title,
            message=message,
        ))
        count += 1

    db.session.commit()
    return jsonify({'success': True, 'sent_to': count})
