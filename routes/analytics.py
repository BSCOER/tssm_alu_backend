"""
Analytics API endpoints for admin dashboard
Provides data for charts and visualizations
"""
from flask import Blueprint, jsonify
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.decorators import admin_required
from database import db, news_collection, alumni_collection, events_collection, jobs_collection
import logging

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/api/v1/admin/analytics/user-growth', methods=['GET'])
@admin_required
def get_user_growth():
    """Get user growth data for line chart (monthly)"""
    try:
        # Get data for last 6 months
        now = datetime.now(timezone.utc)
        months_data = []
        
        for i in range(5, -1, -1):
            # Calculate month start and end
            month_date = now - timedelta(days=30 * i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            if i == 0:
                month_end = now
            else:
                next_month = month_start + timedelta(days=32)
                month_end = next_month.replace(day=1) - timedelta(seconds=1)
            
            # Count total users up to this month
            total_users = db.users.count_documents({
                'created_at': {'$lte': month_end}
            })
            
            # Count new users in this month
            new_users = db.users.count_documents({
                'created_at': {
                    '$gte': month_start,
                    '$lte': month_end
                }
            })
            
            months_data.append({
                'month': month_start.strftime('%b'),
                'totalUsers': total_users,
                'newUsers': new_users
            })
        
        return jsonify({
            'data': months_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user growth: {str(e)}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/v1/admin/analytics/category-distribution', methods=['GET'])
@admin_required
def get_category_distribution():
    """Get article category distribution for pie chart"""
    try:
        # Aggregate articles by category
        pipeline = [
            {'$match': {'status': 'approved'}},
            {'$group': {
                '_id': '$category',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}}
        ]
        
        results = list(news_collection.aggregate(pipeline))
        
        data = [
            {
                'name': item['_id'] or 'Uncategorized',
                'value': item['count']
            }
            for item in results
        ]
        
        return jsonify({
            'data': data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting category distribution: {str(e)}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/v1/admin/analytics/engagement-metrics', methods=['GET'])
@admin_required
def get_engagement_metrics():
    """Get engagement metrics for bar chart (views, reactions, comments)"""
    try:
        # Get data for last 6 months
        now = datetime.now(timezone.utc)
        months_data = []
        
        for i in range(5, -1, -1):
            month_date = now - timedelta(days=30 * i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            if i == 0:
                month_end = now
            else:
                next_month = month_start + timedelta(days=32)
                month_end = next_month.replace(day=1) - timedelta(seconds=1)
            
            # Get articles in this month
            articles = list(news_collection.find({
                'submitted_at': {
                    '$gte': month_start,
                    '$lte': month_end
                }
            }))
            
            # Calculate metrics
            total_views = sum(article.get('views', 0) for article in articles)
            total_reactions = sum(article.get('reaction_count', 0) for article in articles)
            
            # Count comments in this month
            total_comments = db.comments.count_documents({
                'created_at': {
                    '$gte': month_start,
                    '$lte': month_end
                }
            })
            
            months_data.append({
                'month': month_start.strftime('%b'),
                'views': total_views,
                'reactions': total_reactions,
                'comments': total_comments
            })
        
        return jsonify({
            'data': months_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting engagement metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/v1/admin/analytics/alumni-by-year', methods=['GET'])
@admin_required
def get_alumni_by_year():
    """Get alumni distribution by graduation year for bar chart"""
    try:
        # Aggregate alumni by graduation year
        pipeline = [
            {'$match': {'graduation_year': {'$exists': True, '$ne': None}}},
            {'$group': {
                '_id': '$graduation_year',
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}},
            {'$limit': 10}  # Last 10 years
        ]
        
        results = list(alumni_collection.aggregate(pipeline))
        
        data = [
            {
                'year': str(item['_id']),
                'count': item['count']
            }
            for item in results
        ]
        
        return jsonify({
            'data': data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting alumni by year: {str(e)}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/v1/admin/analytics/department-distribution', methods=['GET'])
@admin_required
def get_department_distribution():
    """Get alumni distribution by department for pie chart"""
    try:
        # Aggregate alumni by department
        pipeline = [
            {'$match': {'department': {'$exists': True, '$ne': None, '$ne': ''}}},
            {'$group': {
                '_id': '$department',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}}
        ]
        
        results = list(alumni_collection.aggregate(pipeline))
        
        # Group small departments into "Other"
        threshold = 5
        main_departments = []
        other_count = 0
        
        for item in results:
            if item['count'] >= threshold:
                main_departments.append({
                    'name': item['_id'],
                    'value': item['count']
                })
            else:
                other_count += item['count']
        
        if other_count > 0:
            main_departments.append({
                'name': 'Other',
                'value': other_count
            })
        
        return jsonify({
            'data': main_departments
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting department distribution: {str(e)}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/v1/admin/analytics/recent-activity', methods=['GET'])
@admin_required
def get_recent_activity():
    """Get recent activity feed for dashboard"""
    try:
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        
        # Recent registrations (last 7 days)
        recent_registrations = db.users.count_documents({
            'created_at': {'$gte': week_ago}
        })
        
        # Pending articles
        pending_articles = news_collection.count_documents({
            'status': 'pending'
        })
        
        # Upcoming events (next 30 days)
        month_ahead = now + timedelta(days=30)
        upcoming_events = events_collection.count_documents({
            'event_date': {
                '$gte': now,
                '$lte': month_ahead
            }
        })
        
        activity = [
            {
                'icon': 'user-plus',
                'text': f'{recent_registrations} new registrations in 7 days',
                'time': 'This week'
            },
            {
                'icon': 'newspaper',
                'text': f'{pending_articles} articles pending approval',
                'time': 'Today'
            },
            {
                'icon': 'calendar-alt',
                'text': f'{upcoming_events} upcoming events',
                'time': 'This month'
            }
        ]
        
        return jsonify({
            'activity': activity
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting recent activity: {str(e)}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/v1/admin/analytics/stats-summary', methods=['GET'])
@admin_required
def get_stats_summary():
    """Get summary statistics for stat cards"""
    try:
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Total users
        total_users = db.users.count_documents({})
        
        # Total articles
        total_articles = news_collection.count_documents({})
        
        # Approved articles
        approved_articles = news_collection.count_documents({'status': 'approved'})
        
        # Engagement rate (approved / total)
        engagement_rate = (approved_articles / max(total_articles, 1)) * 100
        
        # Recent registrations (last 7 days)
        recent_registrations = db.users.count_documents({
            'created_at': {'$gte': week_ago}
        })
        
        # Previous week registrations for comparison
        two_weeks_ago = now - timedelta(days=14)
        previous_week_registrations = db.users.count_documents({
            'created_at': {
                '$gte': two_weeks_ago,
                '$lt': week_ago
            }
        })
        
        # Calculate growth percentage
        if previous_week_registrations > 0:
            growth_percentage = ((recent_registrations - previous_week_registrations) / previous_week_registrations) * 100
        else:
            growth_percentage = 100 if recent_registrations > 0 else 0
        
        # Active users (users who logged in last 30 days)
        active_users = db.users.count_documents({
            'last_login': {'$gte': month_ago}
        })
        
        return jsonify({
            'total_users': total_users,
            'total_articles': total_articles,
            'engagement_rate': round(engagement_rate, 1),
            'recent_registrations': recent_registrations,
            'active_users': active_users,
            'growth_percentage': round(growth_percentage, 1)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting stats summary: {str(e)}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/v1/admin/analytics/top-articles', methods=['GET'])
@admin_required
def get_top_articles():
    """Get top performing articles by views and reactions"""
    try:
        # Get top 10 articles by views
        top_by_views = list(news_collection.find(
            {'status': 'approved'},
            {'title': 1, 'views': 1, 'reaction_count': 1, 'submitted_at': 1}
        ).sort('views', -1).limit(10))
        
        # Get top 10 articles by reactions
        top_by_reactions = list(news_collection.find(
            {'status': 'approved'},
            {'title': 1, 'views': 1, 'reaction_count': 1, 'submitted_at': 1}
        ).sort('reaction_count', -1).limit(10))
        
        from utils.helpers import serialize_doc
        
        return jsonify({
            'top_by_views': serialize_doc(top_by_views),
            'top_by_reactions': serialize_doc(top_by_reactions)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting top articles: {str(e)}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/v1/admin/analytics/user-activity-heatmap', methods=['GET'])
@admin_required
def get_user_activity_heatmap():
    """Get user activity heatmap data (day of week and hour)"""
    try:
        # Get all user logins from last 30 days
        now = datetime.now(timezone.utc)
        month_ago = now - timedelta(days=30)
        
        users = list(db.users.find(
            {'last_login': {'$gte': month_ago}},
            {'last_login': 1}
        ))
        
        # Initialize heatmap data
        heatmap = {}
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for day in days:
            heatmap[day] = [0] * 24  # 24 hours
        
        # Count logins by day and hour
        for user in users:
            if user.get('last_login'):
                login_time = user['last_login']
                day_name = days[login_time.weekday()]
                hour = login_time.hour
                heatmap[day_name][hour] += 1
        
        return jsonify({
            'heatmap': heatmap
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user activity heatmap: {str(e)}")
        return jsonify({'error': str(e)}), 500


@analytics_bp.route('/api/v1/admin/analytics/content-performance', methods=['GET'])
@admin_required
def get_content_performance():
    """Get content performance metrics"""
    try:
        # Average views per article
        pipeline_views = [
            {'$match': {'status': 'approved'}},
            {'$group': {
                '_id': None,
                'avg_views': {'$avg': '$views'},
                'total_views': {'$sum': '$views'},
                'max_views': {'$max': '$views'}
            }}
        ]
        
        views_result = list(news_collection.aggregate(pipeline_views))
        views_data = views_result[0] if views_result else {}
        
        # Average reactions per article
        pipeline_reactions = [
            {'$match': {'status': 'approved'}},
            {'$group': {
                '_id': None,
                'avg_reactions': {'$avg': '$reaction_count'},
                'total_reactions': {'$sum': '$reaction_count'}
            }}
        ]
        
        reactions_result = list(news_collection.aggregate(pipeline_reactions))
        reactions_data = reactions_result[0] if reactions_result else {}
        
        # Total comments
        total_comments = db.comments.count_documents({})
        total_articles = news_collection.count_documents({'status': 'approved'})
        avg_comments = total_comments / max(total_articles, 1)
        
        return jsonify({
            'avg_views_per_article': round(views_data.get('avg_views', 0), 1),
            'total_views': views_data.get('total_views', 0),
            'max_views': views_data.get('max_views', 0),
            'avg_reactions_per_article': round(reactions_data.get('avg_reactions', 0), 1),
            'total_reactions': reactions_data.get('total_reactions', 0),
            'avg_comments_per_article': round(avg_comments, 1),
            'total_comments': total_comments
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting content performance: {str(e)}")
        return jsonify({'error': str(e)}), 500
