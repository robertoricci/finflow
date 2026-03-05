from app import db
from datetime import datetime


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(10), nullable=False, default='expense')  # income / expense / both
    icon = db.Column(db.String(50), default='circle')
    color = db.Column(db.String(7), default='#6c757d')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


DEFAULT_CATEGORIES = [
    {'name': 'Alimentação',    'type': 'expense', 'icon': 'utensils',     'color': '#e74c3c'},
    {'name': 'Transporte',     'type': 'expense', 'icon': 'car',          'color': '#e67e22'},
    {'name': 'Moradia',        'type': 'expense', 'icon': 'home',         'color': '#9b59b6'},
    {'name': 'Saúde',          'type': 'expense', 'icon': 'heart-pulse',  'color': '#e91e63'},
    {'name': 'Lazer',          'type': 'expense', 'icon': 'gamepad-2',    'color': '#1abc9c'},
    {'name': 'Comunicação',    'type': 'expense', 'icon': 'smartphone',   'color': '#3498db'},
    {'name': 'Educação',       'type': 'expense', 'icon': 'graduation-cap', 'color': '#f39c12'},
    {'name': 'Outros',         'type': 'expense', 'icon': 'circle-ellipsis', 'color': '#95a5a6'},
    {'name': 'Salário',        'type': 'income',  'icon': 'banknote',     'color': '#27ae60'},
    {'name': 'Freelance',      'type': 'income',  'icon': 'laptop',       'color': '#2ecc71'},
    {'name': 'Investimentos',  'type': 'income',  'icon': 'trending-up',  'color': '#16a085'},
    {'name': 'Outros Ganhos',  'type': 'income',  'icon': 'plus-circle',  'color': '#1abc9c'},
]
