from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar        = db.Column(db.String(200), default=None)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    is_active     = db.Column(db.Boolean, default=True)

    # Perfil e acesso
    role = db.Column(db.String(20), default='prata')  # admin, ouro, prata, bronze

    # Assinatura
    plan_status     = db.Column(db.String(20), default='trial')  # active, trial, overdue, cancelled
    plan_expires_at = db.Column(db.DateTime, default=None)

    # Relationships
    accounts      = db.relationship('Account',      backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    categories    = db.relationship('Category',     backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    transactions  = db.relationship('Transaction',  backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user',  lazy='dynamic', cascade='all, delete-orphan')

    # ── Properties ────────────────────────────────────

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def plan_label(self):
        labels = {'ouro': 'Ouro', 'prata': 'Prata', 'bronze': 'Bronze', 'admin': 'Admin'}
        return labels.get(self.role, self.role.title())

    @property
    def plan_status_label(self):
        labels = {
            'active':    'Ativo',
            'trial':     'Trial',
            'overdue':   'Inadimplente',
            'cancelled': 'Cancelado',
        }
        return labels.get(self.plan_status, self.plan_status)

    @property
    def trial_days_left(self):
        """Dias restantes no trial. Retorna None se nao for trial ou sem data."""
        if self.plan_status != 'trial' or not self.plan_expires_at:
            return None
        delta = self.plan_expires_at - datetime.utcnow()
        return max(0, delta.days)

    @property
    def trial_expired(self):
        """True se o trial ja expirou."""
        if self.plan_status != 'trial' or not self.plan_expires_at:
            return False
        return datetime.utcnow() > self.plan_expires_at

    # ── Methods ───────────────────────────────────────

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'