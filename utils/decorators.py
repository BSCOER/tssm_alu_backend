"""
Custom decorators for route protection
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


def admin_required(fn):
    """Decorator to require admin privileges"""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        from database import db
        
        current_user_id = get_jwt_identity()
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        if not user or not user.get('is_admin', False):
            logger.warning(f"Unauthorized admin access attempt by user: {current_user_id}")
            return jsonify({'error': 'Admin privileges required'}), 403
        return fn(*args, **kwargs)
    return wrapper


def alumni_required(fn):
    """Decorator to require alumni profile (all users are alumni)"""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        # All registered users are considered alumni, just verify they're logged in
        return fn(*args, **kwargs)
    return wrapper
