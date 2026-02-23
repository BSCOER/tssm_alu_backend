"""
Routes package
Contains all API blueprints
"""
from .auth import auth_bp
from .news import news_bp
from .alumni import alumni_bp
from .admin import admin_bp
from .events import events_bp
from .jobs import jobs_bp
from .reactions import reactions_bp
from .health import health_bp

__all__ = [
    'auth_bp',
    'news_bp',
    'alumni_bp',
    'admin_bp',
    'events_bp',
    'jobs_bp',
    'reactions_bp',
    'health_bp'
]
