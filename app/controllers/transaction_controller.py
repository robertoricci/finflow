from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app import db
from app.models.transaction import Transaction
from app.models.account import Account
from datetime import datetime, date, timedelta
import uuid

transaction_bp = Blueprint('transactions', __name__)


def _parse_date(ds):
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(ds, fmt).date()
        except ValueError:
            pass
    return date.today()


def _recalc_balance(account):
    """Recalculate account balance from all paid transactions.
    Cartão de crédito não tem saldo real — seu 'balance' representa a fatura em aberto (negativo).
    """
    from sqlalchemy import func
    if account.account_type == 'credit_card':
        # Fatura em aberto = soma das despesas NÃO pagas
        open_expenses = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.account_id == account.id,
            Transaction.type == 'expense',
            Transaction.paid == False
        ).scalar() or 0
        account.balance = -float(open_expenses)
    else:
        paid_income = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.account_id == account.id,
            Transaction.type == 'income',
            Transaction.paid == True
        ).scalar() or 0
        paid_expense = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.account_id == account.id,
            Transaction.type == 'expense',
            Transaction.paid == True
        ).scalar() or 0
        account.balance = float(paid_income) - float(paid_expense)
    db.session.commit()


@transaction_bp.route('/create', methods=['POST'])
@login_required
def create():
    data = request.get_json()
    ttype = data.get('type')  # income / expense
    description = data.get('description', '').strip()
    amount = float(data.get('amount', 0))
    date_str = data.get('date', '')
    paid = bool(data.get('paid', False))
    paid_at_str = data.get('paid_at', '')
    category_id = data.get('category_id') or None
    account_id = int(data.get('account_id', 0))
    recurrence = int(data.get('recurrence', 0))  # 0=none, 1=monthly, 7=weekly, etc.
    recurrence_times = int(data.get('recurrence_times', 0))
    fixed_day = int(data.get('fixed_day', 0))  # 0=usar dia da data, 1-31=dia fixo do mês
    notes = data.get('notes', '')

    if not description or not ttype or amount <= 0:
        return jsonify({'error': 'Dados inválidos.'}), 400

    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first()
    if not account:
        return jsonify({'error': 'Conta não encontrada.'}), 404

    txn_date = _parse_date(date_str) if date_str else date.today()
    paid_at = _parse_date(paid_at_str) if paid_at_str else (txn_date if paid else None)

    group_id = str(uuid.uuid4()) if recurrence and recurrence_times > 1 else None
    times = recurrence_times if recurrence and recurrence_times > 1 else 1
    is_monthly = recurrence in (1, 2, 3, 6, 12)  # recorrências baseadas em meses

    def next_monthly_date(base_date, months_ahead, day_fixed):
        """Avança N meses e aplica dia fixo se especificado."""
        import calendar
        m = base_date.month + months_ahead * recurrence
        y = base_date.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        target_day = day_fixed if day_fixed and day_fixed > 0 else base_date.day
        max_day = calendar.monthrange(y, m)[1]
        return base_date.replace(year=y, month=m, day=min(target_day, max_day))

    for i in range(times):
        if is_monthly and i > 0:
            t_date = next_monthly_date(txn_date, i, fixed_day)
        elif is_monthly and i == 0 and fixed_day > 0:
            # Primeiro lançamento também usa o dia fixo
            import calendar
            max_day = calendar.monthrange(txn_date.year, txn_date.month)[1]
            t_date = txn_date.replace(day=min(fixed_day, max_day))
        elif not is_monthly:
            t_date = txn_date + timedelta(days=recurrence * i)
        else:
            t_date = txn_date
        t = Transaction(
            user_id=current_user.id,
            account_id=account_id,
            category_id=category_id,
            type=ttype,
            description=description,
            amount=amount,
            date=t_date,
            paid=paid if i == 0 else False,
            paid_at=paid_at if i == 0 else None,
            notes=notes,
            recurrence_group=group_id,
            installment_number=i + 1 if times > 1 else None,
            total_installments=times if times > 1 else None,
        )
        db.session.add(t)

    db.session.commit()
    _recalc_balance(account)

    return jsonify({'success': True, 'message': 'Lançamento criado!'})


@transaction_bp.route('/<int:tid>', methods=['GET'])
@login_required
def get_one(tid):
    t = Transaction.query.filter_by(id=tid, user_id=current_user.id).first_or_404()
    return jsonify(t.to_dict())


@transaction_bp.route('/<int:tid>', methods=['PUT'])
@login_required
def update(tid):
    t = Transaction.query.filter_by(id=tid, user_id=current_user.id).first_or_404()
    data = request.get_json()

    t.description = data.get('description', t.description).strip()
    t.amount = float(data.get('amount', t.amount))
    t.type = data.get('type', t.type)
    t.category_id = data.get('category_id') or None
    if data.get('date'):
        t.date = _parse_date(data['date'])
    t.paid = bool(data.get('paid', t.paid))
    if t.paid and not t.paid_at:
        t.paid_at = date.today()
    t.notes = data.get('notes', t.notes)

    db.session.commit()
    _recalc_balance(t.account)
    return jsonify({'success': True, 'transaction': t.to_dict()})


@transaction_bp.route('/<int:tid>/pay', methods=['POST'])
@login_required
def mark_paid(tid):
    t = Transaction.query.filter_by(id=tid, user_id=current_user.id).first_or_404()
    data = request.get_json() or {}
    paid_at_str = data.get('paid_at', '')
    t.paid = True
    t.paid_at = _parse_date(paid_at_str) if paid_at_str else date.today()
    db.session.commit()
    _recalc_balance(t.account)
    return jsonify({'success': True})


@transaction_bp.route('/<int:tid>/unpay', methods=['POST'])
@login_required
def mark_unpaid(tid):
    t = Transaction.query.filter_by(id=tid, user_id=current_user.id).first_or_404()
    t.paid = False
    t.paid_at = None
    db.session.commit()
    _recalc_balance(t.account)
    return jsonify({'success': True})


@transaction_bp.route('/<int:tid>', methods=['DELETE'])
@login_required
def delete(tid):
    t = Transaction.query.filter_by(id=tid, user_id=current_user.id).first_or_404()
    delete_group = request.args.get('group', 'false') == 'true'
    account = t.account

    if delete_group and t.recurrence_group:
        Transaction.query.filter_by(
            recurrence_group=t.recurrence_group,
            user_id=current_user.id,
            paid=False
        ).delete()
    else:
        db.session.delete(t)

    db.session.commit()
    _recalc_balance(account)
    return jsonify({'success': True})


@transaction_bp.route('/transfer', methods=['POST'])
@login_required
def transfer():
    data = request.get_json()
    from_id = int(data.get('from_account_id', 0))
    to_id = int(data.get('to_account_id', 0))
    amount = float(data.get('amount', 0))
    date_str = data.get('date', '')
    description = data.get('description', 'Transferência')

    if from_id == to_id or amount <= 0:
        return jsonify({'error': 'Dados inválidos.'}), 400

    from_acc = Account.query.filter_by(id=from_id, user_id=current_user.id).first_or_404()
    to_acc = Account.query.filter_by(id=to_id, user_id=current_user.id).first_or_404()
    txn_date = _parse_date(date_str) if date_str else date.today()

    out = Transaction(
        user_id=current_user.id, account_id=from_id, type='expense',
        description=f'Transferência → {to_acc.name}', amount=amount,
        date=txn_date, paid=True, paid_at=txn_date,
    )
    into = Transaction(
        user_id=current_user.id, account_id=to_id, type='income',
        description=f'Transferência ← {from_acc.name}', amount=amount,
        date=txn_date, paid=True, paid_at=txn_date,
    )
    db.session.add(out)
    db.session.add(into)
    db.session.commit()

    _recalc_balance(from_acc)
    _recalc_balance(to_acc)

    return jsonify({'success': True})
