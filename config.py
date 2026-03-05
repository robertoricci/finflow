import os
from datetime import timedelta


def _db_url():
    """
    O Render injeta a URL do PostgreSQL como postgresql://...
    O SQLAlchemy com psycopg3 exige postgresql+psycopg://...
    Esta função faz a conversão automática.
    """
    url = os.environ.get(
        'DATABASE_URL',
        'postgresql+psycopg://finflow_user:finflow_pass@localhost:5432/finflow'
    )
    if url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = _db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig,
}