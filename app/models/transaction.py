from app import db
from datetime import datetime


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    type = db.Column(db.String(10), nullable=False)  # income / expense / transfer
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    date = db.Column(db.Date, nullable=False)
    paid = db.Column(db.Boolean, default=False)
    paid_at = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    recurrence_group = db.Column(db.String(36), nullable=True)  # UUID for grouped recurrences
    installment_number = db.Column(db.Integer, nullable=True)
    total_installments = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'description': self.description,
            'amount': float(self.amount),
            'date': self.date.strftime('%d/%m/%Y'),
            'paid': self.paid,
            'paid_at': self.paid_at.strftime('%d/%m/%Y') if self.paid_at else None,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else 'Sem categoria',
            'category_color': self.category.color if self.category else '#6c757d',
            'account_id': self.account_id,
            'account_name': self.account.name if self.account else '',
            'recurrence_group': self.recurrence_group,
            'installment_number': self.installment_number,
            'total_installments': self.total_installments,
        }

    def __repr__(self):
        return f'<Transaction {self.description} {self.amount}>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'read': self.read,
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M'),
        }
