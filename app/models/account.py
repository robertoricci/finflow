from app import db
from datetime import datetime


class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Numeric(15, 2), default=0.00)
    bank_name = db.Column(db.String(100), default='')
    account_type = db.Column(db.String(50), default='checking')  # checking, savings, cash, credit_card
    color = db.Column(db.String(7), default='#1a73e8')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Campos exclusivos de cartão de crédito
    closing_day = db.Column(db.Integer, nullable=True)   # dia de fechamento da fatura
    due_day     = db.Column(db.Integer, nullable=True)   # dia de vencimento da fatura

    transactions = db.relationship('Transaction', backref='account', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Account {self.name}>'
