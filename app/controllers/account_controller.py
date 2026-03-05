from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.account import Account

account_bp = Blueprint('accounts', __name__)


@account_bp.route('/', methods=['GET'])
@login_required
def list_all():
    accounts = Account.query.filter_by(user_id=current_user.id, is_active=True).all()
    return jsonify([{
        'id': a.id, 'name': a.name,
        'balance': float(a.balance),
        'bank_name': a.bank_name,
        'account_type': a.account_type,
        'color': a.color,
        'closing_day': a.closing_day,
        'due_day': a.due_day,
    } for a in accounts])


@account_bp.route('/', methods=['POST'])
@login_required
def create():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Nome inválido.'}), 400
    acc = Account(
        user_id=current_user.id,
        name=name,
        balance=float(data.get('balance', 0)),
        bank_name=data.get('bank_name', ''),
        account_type=data.get('account_type', 'checking'),
        color=data.get('color', '#1a73e8'),
        closing_day=int(data['closing_day']) if data.get('closing_day') else None,
        due_day=int(data['due_day']) if data.get('due_day') else None,
    )
    db.session.add(acc)
    db.session.commit()
    return jsonify({'success': True, 'id': acc.id, 'name': acc.name})


@account_bp.route('/<int:aid>', methods=['PUT'])
@login_required
def update(aid):
    acc = Account.query.filter_by(id=aid, user_id=current_user.id).first_or_404()
    data = request.get_json()
    acc.name = data.get('name', acc.name).strip()
    acc.bank_name = data.get('bank_name', acc.bank_name)
    acc.account_type = data.get('account_type', acc.account_type)
    acc.color = data.get('color', acc.color)
    acc.closing_day = int(data['closing_day']) if data.get('closing_day') else None
    acc.due_day = int(data['due_day']) if data.get('due_day') else None
    db.session.commit()
    return jsonify({'success': True})


@account_bp.route('/<int:aid>/balance', methods=['PUT'])
@login_required
def adjust_balance(aid):
    acc = Account.query.filter_by(id=aid, user_id=current_user.id).first_or_404()
    data = request.get_json()
    acc.balance = float(data.get('balance', acc.balance))
    db.session.commit()
    return jsonify({'success': True, 'balance': float(acc.balance)})


@account_bp.route('/<int:aid>', methods=['DELETE'])
@login_required
def delete(aid):
    acc = Account.query.filter_by(id=aid, user_id=current_user.id).first_or_404()
    if Account.query.filter_by(user_id=current_user.id, is_active=True).count() <= 1:
        return jsonify({'error': 'Você precisa ter pelo menos uma conta.'}), 400
    acc.is_active = False
    db.session.commit()
    return jsonify({'success': True})

@account_bp.route('/<int:aid>/fatura', methods=['GET'])
@login_required
def get_fatura(aid):
    """Retorna resumo da fatura atual e anterior do cartão."""
    from app.models.transaction import Transaction
    from sqlalchemy import extract
    from datetime import date
    import calendar

    acc = Account.query.filter_by(id=aid, user_id=current_user.id).first_or_404()
    if acc.account_type != 'credit_card':
        return jsonify({'error': 'Não é cartão de crédito.'}), 400

    today = date.today()
    closing = acc.closing_day or 1

    # Calcular período da fatura atual
    if today.day <= closing:
        # Estamos antes do fechamento — fatura atual é do mês passado até hoje
        if today.month == 1:
            fatura_start = date(today.year - 1, 12, closing + 1)
        else:
            prev_month = today.month - 1
            max_day = calendar.monthrange(today.year, prev_month)[1]
            fatura_start = date(today.year, prev_month, min(closing + 1, max_day))
        fatura_end = date(today.year, today.month, closing)
    else:
        # Após o fechamento — fatura atual vai até o próximo fechamento
        fatura_start = date(today.year, today.month, closing + 1)
        if today.month == 12:
            fatura_end = date(today.year + 1, 1, closing)
        else:
            max_day = calendar.monthrange(today.year, today.month + 1)[1]
            fatura_end = date(today.year, today.month + 1, min(closing, max_day))

    # Lançamentos da fatura atual (não pagos)
    txns_open = Transaction.query.filter(
        Transaction.account_id == aid,
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.paid == False,
        Transaction.date >= fatura_start,
        Transaction.date <= fatura_end,
    ).order_by(Transaction.date.desc()).all()

    # Total da fatura atual
    total_open = sum(float(t.amount) for t in txns_open)

    # Calcular vencimento
    due = acc.due_day or acc.closing_day or 10
    if today.day <= closing:
        due_date = date(today.year, today.month, min(due, calendar.monthrange(today.year, today.month)[1]))
    else:
        if today.month == 12:
            due_date = date(today.year + 1, 1, due)
        else:
            due_date = date(today.year, today.month + 1, min(due, calendar.monthrange(today.year, today.month + 1)[1]))

    return jsonify({
        'account_id': aid,
        'account_name': acc.name,
        'fatura_start': fatura_start.strftime('%d/%m/%Y'),
        'fatura_end': fatura_end.strftime('%d/%m/%Y'),
        'due_date': due_date.strftime('%d/%m/%Y'),
        'total': total_open,
        'transactions': [t.to_dict() for t in txns_open],
        'count': len(txns_open),
    })


@account_bp.route('/<int:aid>/pagar-fatura', methods=['POST'])
@login_required
def pagar_fatura(aid):
    """Paga a fatura: debita da conta corrente e marca todos os lançamentos como pagos."""
    from app.models.transaction import Transaction
    from datetime import date
    import uuid

    data = request.get_json()
    source_account_id = int(data.get('source_account_id', 0))
    amount = float(data.get('amount', 0))
    payment_date_str = data.get('payment_date', '')
    transaction_ids = data.get('transaction_ids', [])  # IDs dos lançamentos a quitar

    if not source_account_id or amount <= 0 or not transaction_ids:
        return jsonify({'error': 'Dados inválidos.'}), 400

    card = Account.query.filter_by(id=aid, user_id=current_user.id).first_or_404()
    source = Account.query.filter_by(id=source_account_id, user_id=current_user.id).first_or_404()

    if card.account_type != 'credit_card':
        return jsonify({'error': 'Conta não é cartão de crédito.'}), 400

    from app.controllers.transaction_controller import _recalc_balance, _parse_date
    payment_date = _parse_date(payment_date_str) if payment_date_str else date.today()

    # 1. Marcar lançamentos do cartão como pagos
    txns = Transaction.query.filter(
        Transaction.id.in_(transaction_ids),
        Transaction.user_id == current_user.id,
        Transaction.account_id == aid,
    ).all()
    for t in txns:
        t.paid = True
        t.paid_at = payment_date

    # 2. Criar lançamento de débito na conta de origem (pagamento da fatura)
    pagamento = Transaction(
        user_id=current_user.id,
        account_id=source_account_id,
        type='expense',
        description=f'Pagamento fatura {card.name}',
        amount=amount,
        date=payment_date,
        paid=True,
        paid_at=payment_date,
        notes=f'Pagamento automático de fatura — {len(txns)} lançamento(s) quitado(s)',
    )
    db.session.add(pagamento)
    db.session.commit()

    # 3. Recalcular saldo da conta debitada (cartão não tem saldo real)
    _recalc_balance(source)

    return jsonify({'success': True, 'paid_count': len(txns), 'amount': amount})
