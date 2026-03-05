from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.transaction import Transaction, Notification
from app.models.account import Account
from app.models.category import Category
from datetime import datetime, date
from sqlalchemy import func, extract
import calendar

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    accounts = Account.query.filter_by(user_id=current_user.id, is_active=True).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard/index.html', accounts=accounts, categories=categories)


@dashboard_bp.route('/api/summary')
@login_required
def api_summary():
    account_id = request.args.get('account_id', type=int)
    today = date.today()
    month = request.args.get('month', today.month, type=int)
    year = request.args.get('year', today.year, type=int)

    query = Transaction.query.filter_by(user_id=current_user.id)
    if account_id:
        query = query.filter_by(account_id=account_id)

    # Total balance across accounts
    if account_id:
        account = Account.query.get(account_id)
        balance = float(account.balance) if account else 0
    else:
        bal = db.session.query(func.sum(Account.balance)).filter_by(user_id=current_user.id, is_active=True).scalar()
        balance = float(bal) if bal else 0

    # Overdue (unpaid past due)
    overdue = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.paid == False,
        Transaction.date < today,
        Transaction.type == 'expense'
    )
    if account_id:
        overdue = overdue.filter(Transaction.account_id == account_id)
    overdue_val = float(overdue.scalar() or 0)

    # Monthly income/expense
    monthly_income = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'income',
        extract('month', Transaction.date) == month,
        extract('year', Transaction.date) == year,
    )
    monthly_expense = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        extract('month', Transaction.date) == month,
        extract('year', Transaction.date) == year,
    )
    if account_id:
        monthly_income = monthly_income.filter(Transaction.account_id == account_id)
        monthly_expense = monthly_expense.filter(Transaction.account_id == account_id)

    monthly_income_val = float(monthly_income.scalar() or 0)
    monthly_expense_val = float(monthly_expense.scalar() or 0)

    # Pending count
    pending_count = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.paid == False,
    ).count()

    return jsonify({
        'balance': balance,
        'overdue': overdue_val,
        'monthly_income': monthly_income_val,
        'monthly_expense': monthly_expense_val,
        'pending_count': pending_count,
    })


@dashboard_bp.route('/api/transactions')
@login_required
def api_transactions():
    account_id   = request.args.get('account_id', type=int)
    page         = request.args.get('page', 1, type=int)
    per_page     = request.args.get('per_page', 20, type=int)
    month        = request.args.get('month', type=int)          # None = sem filtro de mês
    year         = request.args.get('year', type=int)
    type_filter  = request.args.get('type', '')
    search       = request.args.get('search', '')
    category_name = request.args.get('category', '')            # filtro por nome de categoria

    query = Transaction.query.filter_by(user_id=current_user.id)
    if account_id:
        query = query.filter_by(account_id=account_id)
    if year:
        query = query.filter(extract('year', Transaction.date) == year)
    if month:
        query = query.filter(extract('month', Transaction.date) == month)
    if type_filter:
        query = query.filter_by(type=type_filter)
    if search:
        query = query.filter(Transaction.description.ilike(f'%{search}%'))
    if category_name:
        from app.models.category import Category
        cat = Category.query.filter_by(user_id=current_user.id, name=category_name).first()
        if cat:
            query = query.filter_by(category_id=cat.id)
        else:
            query = query.filter_by(category_id=None)  # categoria não encontrada = sem resultado

    query = query.order_by(Transaction.date.desc(), Transaction.id.desc())
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'transactions': [t.to_dict() for t in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page,
    })


@dashboard_bp.route('/api/chart/monthly')
@login_required
def api_chart_monthly():
    year = request.args.get('year', date.today().year, type=int)
    account_id = request.args.get('account_id', type=int)

    months_data = []
    for m in range(1, 13):
        income_q = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'income',
            extract('month', Transaction.date) == m,
            extract('year', Transaction.date) == year,
        )
        expense_q = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == 'expense',
            extract('month', Transaction.date) == m,
            extract('year', Transaction.date) == year,
        )
        if account_id:
            income_q = income_q.filter(Transaction.account_id == account_id)
            expense_q = expense_q.filter(Transaction.account_id == account_id)

        months_data.append({
            'month': calendar.month_abbr[m],
            'income': float(income_q.scalar() or 0),
            'expense': float(expense_q.scalar() or 0),
        })

    return jsonify(months_data)


@dashboard_bp.route('/api/chart/categories')
@login_required
def api_chart_categories():
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    ttype = request.args.get('type', 'expense')

    results = db.session.query(
        Category.name,
        Category.color,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction, Transaction.category_id == Category.id).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == ttype,
        extract('month', Transaction.date) == month,
        extract('year', Transaction.date) == year,
    ).group_by(Category.id, Category.name, Category.color).all()

    return jsonify([{'name': r.name, 'color': r.color, 'total': float(r.total)} for r in results])


@dashboard_bp.route('/api/trial-status')
@login_required
def trial_status():
    """Retorna informações do trial do usuário atual."""
    return jsonify({
        'plan_status':    current_user.plan_status,
        'plan_label':     current_user.plan_label,
        'trial_days_left': current_user.trial_days_left,
        'trial_expired':  current_user.trial_expired,
        'plan_expires_at': current_user.plan_expires_at.strftime('%d/%m/%Y') if current_user.plan_expires_at else None,
    })


@dashboard_bp.route('/api/notifications')
@login_required
def api_notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.read.asc(), Notification.created_at.desc()
    ).limit(20).all()
    unread = Notification.query.filter_by(user_id=current_user.id, read=False).count()
    return jsonify({'notifications': [n.to_dict() for n in notifs], 'unread': unread})


@dashboard_bp.route('/api/notifications/read', methods=['POST'])
@login_required
def mark_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, read=False).update({'read': True})
    db.session.commit()
    return jsonify({'success': True})
