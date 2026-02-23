"""
Routes package
Contains all API blueprints
"""
from .health import health_bp
from .analytics import analytics_bp

__all__ = [
    'health_bp',
    'analytics_bp'
]
