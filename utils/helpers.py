"""
Helper utility functions
"""
from bson import ObjectId
from datetime import datetime
import random
import time
import logging

logger = logging.getLogger(__name__)


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


def enrich_article_submitter(article, include_email=False):
    """Normalize submitter info for article responses."""
    from database import db
    
    if not article:
        return

    submitter_id = article.get('submitter_id') or article.get('author_id')
    submitter = None
    submitter_obj_id = None

    if submitter_id:
        if isinstance(submitter_id, ObjectId):
            submitter_obj_id = submitter_id
        else:
            try:
                submitter_obj_id = ObjectId(str(submitter_id))
            except Exception:
                submitter_obj_id = None

    if submitter_obj_id:
        submitter = db.users.find_one({'_id': submitter_obj_id})

    if not submitter and article.get('author'):
        submitter = db.users.find_one({'username': article.get('author')})
        if submitter:
            submitter_obj_id = submitter.get('_id')

    if submitter:
        if submitter_obj_id:
            article['submitter_id'] = str(submitter_obj_id)
        article['submitter_username'] = submitter.get('username')
        article['author_name'] = submitter.get('username')
        if include_email:
            article['submitter_email'] = submitter.get('email')


def generate_otp():
    """Generate 6-digit OTP"""
    return str(random.randint(100000, 999999))


def retry_operation(func, max_retries=3, delay=1):
    """Retry decorator for database operations"""
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Operation failed after {max_retries} attempts: {str(e)}")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(delay * (attempt + 1))
    return wrapper
