from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.transaction import Transaction
from app.models.category import Category
from sqlalchemy import func, extract
from datetime import date

report_bp = Blueprint('reports', __name__)


@report_bp.route('/monthly-expense')
@login_required
def monthly_expense():
    year = request.args.get('year', date.today().year, type=int)
    results = []
    for m in range(1, 13):
        total = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'expense',
            extract('month', Transaction.date) == m,
            extract('year', Transaction.date) == year,
        ).scalar() or 0
        results.append({'month': m, 'total': float(total)})
    return jsonify(results)


@report_bp.route('/monthly-income')
@login_required
def monthly_income():
    year = request.args.get('year', date.today().year, type=int)
    results = []
    for m in range(1, 13):
        total = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'income',
            extract('month', Transaction.date) == m,
            extract('year', Transaction.date) == year,
        ).scalar() or 0
        results.append({'month': m, 'total': float(total)})
    return jsonify(results)


@report_bp.route('/by-category')
@login_required
def by_category():
    month = request.args.get('month', type=int)  # None = ano inteiro
    year  = request.args.get('year', date.today().year, type=int)
    ttype = request.args.get('type', 'expense')

    conditions = (
        (Transaction.category_id == Category.id) &
        (Transaction.user_id == current_user.id) &
        (extract('year', Transaction.date) == year) &
        (Transaction.type == ttype)
    )
    if month:
        conditions = conditions & (extract('month', Transaction.date) == month)

    results = db.session.query(
        Category.name,
        Category.color,
        func.sum(Transaction.amount).label('total'),
        func.count(Transaction.id).label('count')
    ).outerjoin(Transaction, conditions
    ).filter(Category.user_id == current_user.id
    ).group_by(Category.id, Category.name, Category.color).all()

    return jsonify([{
        'name': r.name, 'color': r.color,
        'total': float(r.total or 0), 'count': r.count or 0
    } for r in results])



@report_bp.route('/by-category-annual')
@login_required
def by_category_annual():
    """Retorna despesas por categoria, mês a mês, para o ano inteiro."""
    year  = request.args.get('year', date.today().year, type=int)
    ttype = request.args.get('type', 'expense')

    # Buscar todas as categorias do usuário do tipo correto
    cats = Category.query.filter(
        Category.user_id == current_user.id,
        Category.type.in_([ttype, 'both'])
    ).all()

    result = []
    for cat in cats:
        monthly = []
        total_year = 0.0
        for m in range(1, 13):
            val = float(db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == current_user.id,
                Transaction.type == ttype,
                Transaction.category_id == cat.id,
                extract('month', Transaction.date) == m,
                extract('year',  Transaction.date) == year,
            ).scalar() or 0)
            monthly.append(val)
            total_year += val
        if total_year > 0:
            result.append({
                'id':     cat.id,
                'name':   cat.name,
                'color':  cat.color,
                'monthly': monthly,   # lista de 12 valores
                'total':  total_year,
            })

    result.sort(key=lambda x: x['total'], reverse=True)
    return jsonify(result)

@report_bp.route('/pending')
@login_required
def pending():
    today = date.today()
    overdue = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.paid == False,
        Transaction.date < today,
    ).order_by(Transaction.date.asc()).all()
    upcoming = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.paid == False,
        Transaction.date >= today,
    ).order_by(Transaction.date.asc()).limit(30).all()
    return jsonify({
        'overdue': [t.to_dict() for t in overdue],
        'upcoming': [t.to_dict() for t in upcoming],
    })
