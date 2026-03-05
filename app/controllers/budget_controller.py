from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction
from sqlalchemy import func, extract
from datetime import date

budget_bp = Blueprint('budgets', __name__)


@budget_bp.route('/', methods=['GET'])
@login_required
def list_budgets():
    month = request.args.get('month', type=int)   # None = ano inteiro
    year  = request.args.get('year', date.today().year, type=int)

    q = Budget.query.filter_by(user_id=current_user.id, year=year)
    if month:
        q = q.filter_by(month=month)
    budgets = q.order_by(Budget.month).all()

    result = []
    for b in budgets:
        txn_q = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'expense',
            extract('year', Transaction.date) == (month and year or b.year),
        )
        if month:
            txn_q = txn_q.filter(extract('month', Transaction.date) == month)
        else:
            txn_q = txn_q.filter(extract('month', Transaction.date) == b.month)
        if b.category_id:
            txn_q = txn_q.filter(Transaction.category_id == b.category_id)

        spent = float(txn_q.scalar() or 0)
        budget_amt = float(b.amount)
        pct = round((spent / budget_amt * 100), 1) if budget_amt > 0 else 0

        d = b.to_dict()
        d['spent'] = spent
        d['remaining'] = budget_amt - spent
        d['percent'] = pct
        d['status'] = 'over' if spent > budget_amt else ('warning' if pct >= 80 else 'ok')
        result.append(d)

    return jsonify(result)


@budget_bp.route('/summary', methods=['GET'])
@login_required
def summary():
    """Retorna resumo anual de orçamentos vs gastos reais por mês."""
    year = request.args.get('year', date.today().year, type=int)
    months_data = []
    for m in range(1, 13):
        total_budget = db.session.query(func.sum(Budget.amount)).filter(
            Budget.user_id == current_user.id,
            Budget.month == m,
            Budget.year == year,
        ).scalar() or 0

        total_spent = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'expense',
            extract('month', Transaction.date) == m,
            extract('year', Transaction.date) == year,
        ).scalar() or 0

        months_data.append({
            'month': m,
            'budget': float(total_budget),
            'spent': float(total_spent),
        })
    return jsonify(months_data)


@budget_bp.route('/detail', methods=['GET'])
@login_required
def detail():
    """Retorna gastos detalhados por categoria. Se month omitido, retorna ano inteiro."""
    month = request.args.get('month', type=int)   # None = ano inteiro
    year  = request.args.get('year', date.today().year, type=int)

    cats = Category.query.filter(
        Category.user_id == current_user.id,
        Category.type.in_(['expense', 'both'])
    ).all()

    # Buscar budgets: se mês específico, filtra; senão, soma todos os orçamentos do ano
    budgets_map = {}
    bq = Budget.query.filter_by(user_id=current_user.id, year=year)
    if month:
        bq = bq.filter_by(month=month)
    for b in bq.all():
        if b.category_id not in budgets_map:
            budgets_map[b.category_id] = 0.0
        budgets_map[b.category_id] += float(b.amount)

    result = []
    for cat in cats:
        txn_q = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'expense',
            Transaction.category_id == cat.id,
            extract('year', Transaction.date) == year,
        )
        if month:
            txn_q = txn_q.filter(extract('month', Transaction.date) == month)

        txns = txn_q.order_by(Transaction.date.desc()).all()
        spent = sum(float(t.amount) for t in txns)

        if spent == 0 and cat.id not in budgets_map:
            continue

        budget_amt = budgets_map.get(cat.id, 0)
        pct = round((spent / budget_amt * 100), 1) if budget_amt > 0 else None
        status = None
        if budget_amt > 0:
            status = 'over' if spent > budget_amt else ('warning' if pct >= 80 else 'ok')

        result.append({
            'category_id': cat.id,
            'category_name': cat.name,
            'category_color': cat.color,
            'budget_id': None,
            'budget': budget_amt,
            'spent': spent,
            'remaining': budget_amt - spent if budget_amt > 0 else None,
            'percent': pct,
            'status': status,
            'transactions': [t.to_dict() for t in txns],
        })

    result.sort(key=lambda x: x['spent'], reverse=True)
    return jsonify(result)


@budget_bp.route('/', methods=['POST'])
@login_required
def create():
    data = request.get_json()
    month = int(data.get('month', date.today().month))
    year = int(data.get('year', date.today().year))
    category_id = int(data.get('category_id')) if data.get('category_id') else None
    amount = float(data.get('amount', 0))
    recurrence = int(data.get('recurrence', 0))       # 0=sem, 1=mensal, 2=bimestral etc
    recurrence_times = int(data.get('recurrence_times', 1))

    if amount <= 0:
        return jsonify({'error': 'Valor inválido.'}), 400

    created = []
    cur_month, cur_year = month, year

    times = recurrence_times if recurrence > 0 else 1
    for i in range(times):
        # Upsert: se já existe para esse mês/ano, atualiza
        existing = Budget.query.filter_by(
            user_id=current_user.id,
            category_id=category_id,
            month=cur_month,
            year=cur_year,
        ).first()

        if existing:
            existing.amount = amount
        else:
            b = Budget(
                user_id=current_user.id,
                category_id=category_id,
                month=cur_month,
                year=cur_year,
                amount=amount,
            )
            db.session.add(b)
            created.append({'month': cur_month, 'year': cur_year})

        # Avançar meses conforme recurrence
        if recurrence > 0:
            cur_month += recurrence
            while cur_month > 12:
                cur_month -= 12
                cur_year += 1

    db.session.commit()
    return jsonify({'success': True, 'created': len(created), 'updated': times - len(created)})


@budget_bp.route('/<int:bid>', methods=['PUT'])
@login_required
def update(bid):
    b = Budget.query.filter_by(id=bid, user_id=current_user.id).first_or_404()
    data = request.get_json()
    b.amount = float(data.get('amount', b.amount))
    db.session.commit()
    return jsonify({'success': True})


@budget_bp.route('/<int:bid>', methods=['DELETE'])
@login_required
def delete(bid):
    b = Budget.query.filter_by(id=bid, user_id=current_user.id).first_or_404()
    db.session.delete(b)
    db.session.commit()
    return jsonify({'success': True})
