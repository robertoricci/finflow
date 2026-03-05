from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.category import Category

category_bp = Blueprint('categories', __name__)


@category_bp.route('/', methods=['GET'])
@login_required
def list_all():
    cats = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    return jsonify([{
        'id': c.id, 'name': c.name, 'type': c.type,
        'icon': c.icon, 'color': c.color
    } for c in cats])


@category_bp.route('/', methods=['POST'])
@login_required
def create():
    data = request.get_json()
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Nome inválido.'}), 400
    cat = Category(
        user_id=current_user.id,
        name=name,
        type=data.get('type', 'expense'),
        icon=data.get('icon', 'circle'),
        color=data.get('color', '#6c757d'),
    )
    db.session.add(cat)
    db.session.commit()
    return jsonify({'success': True, 'id': cat.id, 'name': cat.name})


@category_bp.route('/<int:cid>', methods=['PUT'])
@login_required
def update(cid):
    cat = Category.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    data = request.get_json()
    cat.name = data.get('name', cat.name).strip()
    cat.type = data.get('type', cat.type)
    cat.icon = data.get('icon', cat.icon)
    cat.color = data.get('color', cat.color)
    db.session.commit()
    return jsonify({'success': True})


@category_bp.route('/<int:cid>', methods=['DELETE'])
@login_required
def delete(cid):
    cat = Category.query.filter_by(id=cid, user_id=current_user.id).first_or_404()
    db.session.delete(cat)
    db.session.commit()
    return jsonify({'success': True})
