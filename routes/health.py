"""
Health check and monitoring routes
"""
from flask import Blueprint, jsonify
from utils.decorators import admin_required
from database import db

health_bp = Blueprint('health', __name__)


@health_bp.route("/", methods=["GET", "HEAD"])
def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "TSSM Alumni Backend",
        "version": "1.0.0"
    }, 200


@health_bp.route('/api/v1/metrics', methods=['GET'])
@admin_required
def get_metrics():
    """Get API metrics (admin only)"""
    try:
        from database import news_collection, alumni_collection, events_collection, jobs_collection
        from datetime import datetime, timezone
        
        metrics = {
            'total_users': db.users.count_documents({}),
            'total_alumni': alumni_collection.count_documents({}),
            'total_articles': news_collection.count_documents({}),
            'pending_articles': news_collection.count_documents({'status': 'pending'}),
            'total_events': events_collection.count_documents({}),
            'total_jobs': jobs_collection.count_documents({}),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        return jsonify(metrics), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
