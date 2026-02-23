"""
Database connection and initialization
Handles MongoDB connection and index creation
"""
from pymongo import MongoClient, ASCENDING, DESCENDING
import logging

logger = logging.getLogger(__name__)

# Global database references
client = None
db = None
news_collection = None
alumni_collection = None
events_collection = None
jobs_collection = None
comments_collection = None
email_announcements_collection = None
gallery_collection = None
startups_collection = None


def init_database(app):
    """Initialize MongoDB connection and collections"""
    global client, db, news_collection, alumni_collection, events_collection
    global jobs_collection, comments_collection, email_announcements_collection
    global gallery_collection, startups_collection
    
    mongodb_uri = app.config['MONGODB_URI']
    
    if not mongodb_uri:
        logger.error("MONGODB_URI not set in configuration!")
        raise ValueError("MONGODB_URI configuration is required")
    
    try:
        client = MongoClient(mongodb_uri, **app.config['MONGODB_SETTINGS'])
        
        # Test connection
        client.admin.command('ping')
        
        db = client.get_default_database()
        news_collection = db.news
        alumni_collection = db.alumni
        events_collection = db.events
        jobs_collection = db.jobs
        comments_collection = db.comments
        email_announcements_collection = db.email_announcements
        gallery_collection = db.alumni_gallery
        startups_collection = db.student_startups
        
        logger.info("MongoDB connected successfully")
        
        # Create indexes
        create_indexes()
        
        return db
        
    except Exception as e:
        logger.error(f"MongoDB connection failed: {str(e)}")
        raise


def create_indexes():
    """Create database indexes for optimized queries"""
    if db is None:
        logger.warning("Skipping index creation - database not connected")
        return
    
    try:
        # News indexes
        news_collection.create_index([("status", ASCENDING)])
        news_collection.create_index([("submitter_id", ASCENDING)])
        news_collection.create_index([("submitted_at", DESCENDING)])
        news_collection.create_index([("tags", ASCENDING)])
        news_collection.create_index([("title", "text"), ("content", "text")])
        
        # Alumni indexes
        alumni_collection.create_index([("user_id", ASCENDING)], unique=True)
        alumni_collection.create_index([("graduation_year", ASCENDING)])
        alumni_collection.create_index([("batch", ASCENDING)])
        alumni_collection.create_index([("department", ASCENDING)])
        
        # Users indexes
        db.users.create_index([("email", ASCENDING)], unique=True)
        db.users.create_index([("username", ASCENDING)], unique=True)
        
        # Events indexes
        events_collection.create_index([("event_date", DESCENDING)])
        events_collection.create_index([("status", ASCENDING)])
        
        # Jobs indexes
        jobs_collection.create_index([("posted_at", DESCENDING)])
        jobs_collection.create_index([("company", ASCENDING)])
        
        # Email announcements indexes
        email_announcements_collection.create_index([("sent_at", DESCENDING)])
        email_announcements_collection.create_index([("sent_by", ASCENDING)])
        email_announcements_collection.create_index([("status", ASCENDING)])
        
        # Comments indexes
        db.comments.create_index([("article_id", ASCENDING)])
        db.comments.create_index([("user_id", ASCENDING)])
        db.comments.create_index([("parent_id", ASCENDING)])
        db.comments.create_index([("created_at", DESCENDING)])
        
        # Achievements indexes
        db.achievements.create_index([("category", ASCENDING)])
        db.achievements.create_index([("is_featured", DESCENDING), ("created_at", DESCENDING)])
        
        # Alumni gallery indexes
        db.alumni_gallery.create_index([("year", DESCENDING), ("created_at", DESCENDING)])
        db.alumni_gallery.create_index([("created_by", ASCENDING)])
        
        # Student startup indexes
        db.student_startups.create_index([("year", DESCENDING), ("created_at", DESCENDING)])
        db.student_startups.create_index([("is_featured", DESCENDING), ("created_at", DESCENDING)])
        
        # Achievement comments indexes
        db.achievement_comments.create_index([("achievement_id", ASCENDING), ("created_at", DESCENDING)])
        db.achievement_comments.create_index([("user_id", ASCENDING)])
        
        # Notifications indexes
        db.notifications.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        db.notifications.create_index([("is_read", ASCENDING), ("created_at", DESCENDING)])
        
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")


def get_db():
    """Get database instance"""
    return db
