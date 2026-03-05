from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.models.account import Account
from app.models.category import Category, DEFAULT_CATEGORIES
from app.models.transaction import Notification

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        flash('E-mail ou senha inválidos.', 'danger')
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if not name or not email or not password:
            flash('Preencha todos os campos.', 'danger')
            return render_template('auth/register.html')
        if password != confirm:
            flash('As senhas não coincidem.', 'danger')
            return render_template('auth/register.html')
        if len(password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
            return render_template('auth/register.html')
        if User.query.filter_by(email=email).first():
            flash('Este e-mail já está em uso.', 'danger')
            return render_template('auth/register.html')
        trial_expires = datetime.utcnow() + timedelta(days=15)
        user = User(
            name=name, email=email,
            plan_status='trial',
            plan_expires_at=trial_expires,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # Default account
        account = Account(user_id=user.id, name='Conta Principal', balance=0.00, color='#1a73e8')
        db.session.add(account)

        # Default categories
        for cat in DEFAULT_CATEGORIES:
            db.session.add(Category(user_id=user.id, **cat))

        # Welcome notification
        notif = Notification(
            user_id=user.id,
            title='Bem-vindo ao FinFlow!',
            message=f'Olá {name}, seja bem-vindo ao FinFlow! Seu controle financeiro começa agora.'
        )
        db.session.add(notif)
        db.session.commit()

        login_user(user)
        flash('Conta criada com sucesso! Bem-vindo ao FinFlow.', 'success')
        return redirect(url_for('dashboard.index'))
    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        if name:
            current_user.name = name
        if current_password and new_password:
            if not current_user.check_password(current_password):
                flash('Senha atual incorreta.', 'danger')
                return render_template('auth/profile.html')
            if len(new_password) < 6:
                flash('A nova senha deve ter pelo menos 6 caracteres.', 'danger')
                return render_template('auth/profile.html')
            current_user.set_password(new_password)
        db.session.commit()
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('auth.profile'))
    return render_template('auth/profile.html')
