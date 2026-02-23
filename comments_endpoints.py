"""
Comments API Endpoints
Handles article comments with nested threading support
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime
import logging
import re

# Will be initialized from app.py
comments_bp = Blueprint('comments', __name__)
db = None
logger = None
MENTION_PATTERN = re.compile(r'(?<!\w)@([A-Za-z0-9_]{3,50})')

def init_comments_blueprint(database, app_logger):
    """Initialize blueprint with database and logger"""
    global db, logger
    db = database
    logger = app_logger


def create_comment_mention_notifications(content, actor_user_id, actor_username, article_id):
    if not content:
        return

    mentions = MENTION_PATTERN.findall(str(content))
    if not mentions:
        return

    seen = set()
    notifications = []

    for username in mentions:
        key = username.lower()
        if key in seen:
            continue
        seen.add(key)

        mentioned_user = db.users.find_one({'username': {'$regex': f'^{re.escape(username)}$', '$options': 'i'}})
        if not mentioned_user:
            continue

        if str(mentioned_user.get('_id')) == str(actor_user_id):
            continue

        notifications.append({
            'user_id': mentioned_user.get('_id'),
            'type': 'mention',
            'title': 'You were mentioned',
            'message': f'@{actor_username or "Someone"} mentioned you in a comment.',
            'context_type': 'news comment',
            'context_id': str(article_id),
            'preview_text': str(content)[:240],
            'actor_user_id': ObjectId(actor_user_id),
            'actor_username': actor_username,
            'is_read': False,
            'created_at': datetime.utcnow()
        })

    if notifications:
        db.notifications.insert_many(notifications)

def serialize_doc(doc):
    """Convert MongoDB document to JSON serializable format"""
    if doc is None:
        return None
    if isinstance(doc, ObjectId):
        return str(doc)
    if isinstance(doc, datetime):
        return doc.isoformat()
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        doc = doc.copy()
        if '_id' in doc:
            doc['_id'] = str(doc['_id'])
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                doc[key] = str(value)
            elif isinstance(value, datetime):
                doc[key] = value.isoformat()
            elif isinstance(value, dict):
                doc[key] = serialize_doc(value)
            elif isinstance(value, list):
                doc[key] = serialize_doc(value)
        return doc
    return doc


@comments_bp.route('/api/v1/articles/<article_id>/comments', methods=['POST'])
@jwt_required()
def create_comment(article_id):
    """Create a new comment on an article"""
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'error': 'Comment content is required'}), 400
        
        if len(content) > 1000:
            return jsonify({'error': 'Comment too long (max 1000 characters)'}), 400
        
        # Verify article exists
        article = db.news.find_one({'_id': ObjectId(article_id)})
        if not article:
            return jsonify({'error': 'Article not found'}), 404
        
        # Get current user
        user_id = get_jwt_identity()
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Create comment document
        comment = {
            'article_id': ObjectId(article_id),
            'user_id': ObjectId(user_id),
            'author_name': user.get('full_name', user.get('email', 'Anonymous')),
            'author_image': user.get('profile_image'),
            'content': content,
            'parent_id': None,  # Top-level comment
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'is_edited': False
        }
        
        result = db.comments.insert_one(comment)
        comment['_id'] = result.inserted_id

        create_comment_mention_notifications(
            content,
            user_id,
            user.get('username'),
            article_id
        )
        
        # Update article comment count
        db.news.update_one(
            {'_id': ObjectId(article_id)},
            {'$inc': {'comment_count': 1}}
        )
        
        logger.info(f"Comment created on article {article_id} by user {user_id}")
        
        return jsonify({
            'message': 'Comment created successfully',
            'comment': serialize_doc(comment)
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating comment: {str(e)}")
        return jsonify({'error': str(e)}), 500


@comments_bp.route('/api/v1/articles/<article_id>/comments', methods=['GET'])
def get_comments(article_id):
    """Get all comments for an article (nested structure)"""
    try:
        # Verify article exists
        article = db.news.find_one({'_id': ObjectId(article_id)})
        if not article:
            return jsonify({'error': 'Article not found'}), 404
        
        # Get all comments for this article
        all_comments = list(db.comments.find(
            {'article_id': ObjectId(article_id)}
        ).sort('created_at', -1))
        
        # Separate top-level comments and replies
        top_level = []
        replies_map = {}
        
        for comment in all_comments:
            comment_dict = serialize_doc(comment)
            
            if comment.get('parent_id') is None:
                comment_dict['replies'] = []
                top_level.append(comment_dict)
            else:
                parent_id = str(comment['parent_id'])
                if parent_id not in replies_map:
                    replies_map[parent_id] = []
                replies_map[parent_id].append(comment_dict)
        
        # Attach replies to their parent comments
        def attach_replies(comment):
            comment_id = comment['_id']
            if comment_id in replies_map:
                comment['replies'] = replies_map[comment_id]
                # Recursively attach nested replies
                for reply in comment['replies']:
                    attach_replies(reply)
            return comment
        
        top_level = [attach_replies(comment) for comment in top_level]
        
        return jsonify({
            'comments': top_level,
            'total': len(all_comments)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching comments: {str(e)}")
        return jsonify({'error': str(e)}), 500


@comments_bp.route('/api/v1/comments/<comment_id>/reply', methods=['POST'])
@jwt_required()
def reply_to_comment(comment_id):
    """Reply to an existing comment"""
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'error': 'Reply content is required'}), 400
        
        if len(content) > 1000:
            return jsonify({'error': 'Reply too long (max 1000 characters)'}), 400
        
        # Verify parent comment exists
        parent_comment = db.comments.find_one({'_id': ObjectId(comment_id)})
        if not parent_comment:
            return jsonify({'error': 'Parent comment not found'}), 404
        
        # Get current user
        user_id = get_jwt_identity()
        user = db.users.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Create reply document
        reply = {
            'article_id': parent_comment['article_id'],
            'user_id': ObjectId(user_id),
            'author_name': user.get('full_name', user.get('email', 'Anonymous')),
            'author_image': user.get('profile_image'),
            'content': content,
            'parent_id': ObjectId(comment_id),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'is_edited': False
        }
        
        result = db.comments.insert_one(reply)
        reply['_id'] = result.inserted_id

        create_comment_mention_notifications(
            content,
            user_id,
            user.get('username'),
            str(parent_comment['article_id'])
        )
        
        # Update article comment count
        db.news.update_one(
            {'_id': parent_comment['article_id']},
            {'$inc': {'comment_count': 1}}
        )
        
        logger.info(f"Reply created on comment {comment_id} by user {user_id}")
        
        return jsonify({
            'message': 'Reply created successfully',
            'comment': serialize_doc(reply)
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating reply: {str(e)}")
        return jsonify({'error': str(e)}), 500


@comments_bp.route('/api/v1/comments/<comment_id>', methods=['PUT'])
@jwt_required()
def update_comment(comment_id):
    """Update user's own comment"""
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        
        if not content:
            return jsonify({'error': 'Comment content is required'}), 400
        
        if len(content) > 1000:
            return jsonify({'error': 'Comment too long (max 1000 characters)'}), 400
        
        # Get current user
        user_id = get_jwt_identity()
        
        # Check if comment exists and belongs to user
        comment = db.comments.find_one({'_id': ObjectId(comment_id)})
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        
        if str(comment['user_id']) != user_id:
            return jsonify({'error': 'Unauthorized to edit this comment'}), 403
        
        # Update comment
        db.comments.update_one(
            {'_id': ObjectId(comment_id)},
            {
                '$set': {
                    'content': content,
                    'updated_at': datetime.utcnow(),
                    'is_edited': True
                }
            }
        )

        create_comment_mention_notifications(
            content,
            user_id,
            user.get('username'),
            str(comment.get('article_id'))
        )
        
        # Get updated comment
        updated_comment = db.comments.find_one({'_id': ObjectId(comment_id)})
        
        logger.info(f"Comment {comment_id} updated by user {user_id}")
        
        return jsonify({
            'message': 'Comment updated successfully',
            'comment': serialize_doc(updated_comment)
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating comment: {str(e)}")
        return jsonify({'error': str(e)}), 500


@comments_bp.route('/api/v1/comments/<comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(comment_id):
    """Delete user's own comment"""
    try:
        # Get current user
        user_id = get_jwt_identity()
        
        # Check if comment exists and belongs to user
        comment = db.comments.find_one({'_id': ObjectId(comment_id)})
        if not comment:
            return jsonify({'error': 'Comment not found'}), 404
        
        if str(comment['user_id']) != user_id:
            return jsonify({'error': 'Unauthorized to delete this comment'}), 403
        
        # Count all nested replies to decrement article comment count
        def count_all_replies(parent_id):
            replies = list(db.comments.find({'parent_id': ObjectId(parent_id)}))
            count = len(replies)
            for reply in replies:
                count += count_all_replies(str(reply['_id']))
            return count
        
        total_to_delete = 1 + count_all_replies(comment_id)
        
        # Delete comment and all nested replies
        db.comments.delete_many({
            '$or': [
                {'_id': ObjectId(comment_id)},
                {'parent_id': ObjectId(comment_id)}
            ]
        })
        
        # Update article comment count
        db.news.update_one(
            {'_id': comment['article_id']},
            {'$inc': {'comment_count': -total_to_delete}}
        )
        
        logger.info(f"Comment {comment_id} and {total_to_delete-1} replies deleted by user {user_id}")
        
        return jsonify({
            'message': 'Comment deleted successfully',
            'deleted_count': total_to_delete
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting comment: {str(e)}")
        return jsonify({'error': str(e)}), 500
