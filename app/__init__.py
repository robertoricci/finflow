from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'info'


def create_app(config_name='default'):
    app = Flask(__name__, template_folder='views/templates')
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.controllers.auth_controller import auth_bp
    from app.controllers.dashboard_controller import dashboard_bp
    from app.controllers.transaction_controller import transaction_bp
    from app.controllers.category_controller import category_bp
    from app.controllers.account_controller import account_bp
    from app.controllers.report_controller import report_bp
    from app.controllers.budget_controller import budget_bp
    from app.controllers.admin_controller import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(transaction_bp, url_prefix='/transactions')
    app.register_blueprint(category_bp, url_prefix='/categories')
    app.register_blueprint(account_bp, url_prefix='/accounts')
    app.register_blueprint(report_bp, url_prefix='/reports')
    app.register_blueprint(budget_bp, url_prefix='/budgets')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    return app
