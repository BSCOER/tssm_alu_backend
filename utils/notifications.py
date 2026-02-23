"""
Notification utility functions
"""
import re
from datetime import datetime, timezone
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

MENTION_PATTERN = re.compile(r'(?<!\w)@([A-Za-z0-9_]{3,50})')


def extract_usernames_from_mentions(text):
    """Extract unique mentioned usernames from text like @username"""
    if not text:
        return []
    mentions = MENTION_PATTERN.findall(str(text))
    seen = set()
    unique_mentions = []
    for username in mentions:
        key = username.lower()
        if key not in seen:
            seen.add(key)
            unique_mentions.append(username)
    return unique_mentions


def create_mention_notifications(text, actor_user_id, actor_username, context_type, context_id, preview_text=''):
    """Create mention notifications for users referenced with @username"""
    from database import db
    
    usernames = extract_usernames_from_mentions(text)
    if not usernames or db is None:
        return 0

    notifications = []
    for username in usernames:
        mentioned_user = db.users.find_one({'username': {'$regex': f'^{re.escape(username)}$', '$options': 'i'}})
        if not mentioned_user:
            continue

        mentioned_user_id = str(mentioned_user.get('_id'))
        if actor_user_id and mentioned_user_id == str(actor_user_id):
            continue

        notifications.append({
            'user_id': mentioned_user.get('_id'),
            'type': 'mention',
            'title': 'You were mentioned',
            'message': f'@{actor_username or "Someone"} mentioned you in {context_type}.',
            'context_type': context_type,
            'context_id': str(context_id),
            'preview_text': str(preview_text or '')[:240],
            'actor_user_id': ObjectId(actor_user_id) if actor_user_id else None,
            'actor_username': actor_username,
            'is_read': False,
            'created_at': datetime.now(timezone.utc)
        })

    if notifications:
        db.notifications.insert_many(notifications)
    return len(notifications)
