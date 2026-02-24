from flask import Flask, request, jsonify, current_app
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_compress import Compress
from pymongo import MongoClient, ASCENDING, DESCENDING
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import cloudinary
import cloudinary.uploader
import cloudinary.api
import random
import requests
import markdown
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
import time
import json
import threading
import csv
import io
import re

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24).hex())
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', os.urandom(24).hex())
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

# Cache configuration - Optimized for high traffic
app.config['CACHE_TYPE'] = 'SimpleCache'  # Use Redis in production for better performance
app.config['CACHE_DEFAULT_TIMEOUT'] = 600  # 10 minutes
app.config['CACHE_THRESHOLD'] = 1000  # Maximum number of cached items

# Compression configuration for better performance
app.config['COMPRESS_MIMETYPES'] = [
    'text/html', 'text/css', 'text/xml', 'application/json',
    'application/javascript', 'text/javascript'
]
app.config['COMPRESS_LEVEL'] = 6  # Compression level (1-9, default 6)
app.config['COMPRESS_MIN_SIZE'] = 500  # Only compress responses larger than 500 bytes

# Initialize extensions
CORS(app, resources={
    r"/api/*": {
        "origins": [
            
            "https://bscoeralumni.vercel.app",
            "https://bscoer.vercel.app",
            
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})
jwt = JWTManager(app)
cache = Cache(app)
compress = Compress(app)

# Rate limiting configuration
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["10000 per day", "1000 per hour"],
    storage_uri="memory://"  # Use Redis in production: "redis://localhost:6379"
)

# Logging configuration
if not os.path.exists('logs'):
    os.mkdir('logs')

file_handler = RotatingFileHandler('logs/alumni_api.log', maxBytes=10240000, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Alumni API startup')

# Brevo (formerly Sendinblue) Email Configuration
BREVO_SMTP_SERVER = os.getenv('BREVO_SMTP_SERVER', 'smtp-relay.brevo.com')
BREVO_SMTP_PORT = int(os.getenv('BREVO_SMTP_PORT', '587'))
BREVO_EMAIL = os.getenv('BREVO_EMAIL')  # Your Brevo account email
BREVO_API_KEY = os.getenv('BREVO_API_KEY')  # Brevo SMTP key/password
BREVO_API_URL = os.getenv('BREVO_API_URL', 'https://api.brevo.com/v3/smtp/email')

# Fallback to Gmail if Brevo not configured
GMAIL_EMAIL = os.getenv('GMAIL_EMAIL')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# MongoDB connection with optimized connection pooling for high traffic
MONGODB_URI = os.getenv('MONGODB_URI')
if not MONGODB_URI:
    app.logger.error("MONGODB_URI not set in environment variables!")
    raise ValueError("MONGODB_URI environment variable is required")

db = None
news_collection = None
alumni_collection = None
events_collection = None
jobs_collection = None
comments_collection = None
email_announcements_collection = None
gallery_collection = None
startups_collection = None

try:
    client = MongoClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=15000,
        retryWrites=True,
        connectTimeoutMS=15000,
        maxPoolSize=50,  # Increased for high traffic
        minPoolSize=10,   # Keep minimum connections open
        maxIdleTimeMS=45000,
        waitQueueTimeoutMS=10000,
        # Compression for better performance
        compressors='snappy,zlib',
        zlibCompressionLevel=6
    )
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
    app.logger.info("MongoDB connected successfully")
except Exception as e:
    app.logger.error(f"MongoDB connection failed: {str(e)}")
    # Continue with None - routes will handle gracefully

# Create indexes for better performance
def create_indexes():
    """Create database indexes for optimized queries"""
    if news_collection is None:
        app.logger.warning("Skipping index creation - database not connected")
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
        
        app.logger.info("Database indexes created successfully")
    except Exception as e:
        app.logger.error(f"Error creating indexes: {str(e)}")

# Create indexes on startup
with app.app_context():
    create_indexes()
    # Clear cache on startup (important for DB migrations/changes)
    cache.clear()
    app.logger.info("Cache cleared on startup")

# API Version
API_VERSION = "v1"

# ============ HELPER FUNCTIONS ============

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

def admin_required(fn):
    """Decorator to require admin privileges"""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        if not user or not user.get('is_admin', False):
            app.logger.warning(f"Unauthorized admin access attempt by user: {current_user_id}")
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

def db_check():
    """Check if database is available, return error response if not"""
    if news_collection is None:
        return jsonify({'error': 'Database unavailable. Please try again later.'}), 503
    return None

def get_current_user():
    """Get current user from JWT token"""
    if db is None:
        return None
    current_user_id = get_jwt_identity()
    user = db.users.find_one({'_id': ObjectId(current_user_id)})
    return serialize_doc(user) if user else None

def generate_otp():
    """Generate 6-digit OTP"""
    return str(random.randint(100000, 999999))


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

def retry_operation(func, max_retries=3, delay=1):
    """Retry decorator for database operations"""
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    app.logger.error(f"Operation failed after {max_retries} attempts: {str(e)}")
                    raise
                app.logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(delay * (attempt + 1))
    return wrapper

def can_send_email():
    if BREVO_EMAIL and BREVO_API_KEY:
        return True
    if GMAIL_EMAIL and GMAIL_APP_PASSWORD:
        return True
    app.logger.error("No email service configured")
    return False

def send_email_async(subject, message, recipient_email):
    """Send email in a background thread to avoid blocking requests."""
    if not can_send_email():
        return False

    def _task():
        try:
            send_email_via_gmail(subject, message, recipient_email)
        except Exception as e:
            app.logger.error(f"Async email error: {str(e)}")

    thread = threading.Thread(target=_task, daemon=True)
    thread.start()
    return True

def send_email_via_gmail(subject, message, recipient_email):
    """Send email via Brevo HTTP API (primary) or Gmail (fallback) SMTP with retry mechanism"""
    @retry_operation
    def _send():
        # Try Brevo HTTP API first
        if BREVO_EMAIL and BREVO_API_KEY:
            app.logger.info("Using Brevo for email delivery")
            payload = {
                "sender": {"name": "TSSM Alumni Portal", "email": BREVO_EMAIL},
                "to": [{"email": recipient_email}],
                "subject": subject,
                "htmlContent": message,
            }
            headers = {
                "accept": "application/json",
                "api-key": BREVO_API_KEY,
                "content-type": "application/json",
            }
            response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        # Fallback to Gmail
        elif GMAIL_EMAIL and GMAIL_APP_PASSWORD:
            settings = db.settings.find_one() or {}
            smtp_server = settings.get('smtp_server', 'smtp.gmail.com')
            smtp_port = int(settings.get('smtp_port', '587'))
            sender_email = GMAIL_EMAIL
            sender_password = GMAIL_APP_PASSWORD
            app.logger.info("Using Gmail for email delivery")
        else:
            app.logger.error("No email service configured")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = f"TSSM Alumni Portal <{sender_email}>"
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 10px;">
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                            <h1 style="color: white; margin: 0;">🎓 TSSM Alumni Portal</h1>
                        </div>
                        <div style="padding: 30px; background-color: #f8f9fa;">
                            {message}
                        </div>
                        <div style="background-color: #f0f0f0; padding: 20px; text-align: center; border-radius: 0 0 10px 10px;">
                            <p style="color: #666; margin: 0; font-size: 12px;">© 2026 TSSM Alumni Portal. All rights reserved.</p>
                        </div>
                    </div>
                </body>
            </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        return True
    
    try:
        return _send()
    except Exception as e:
        app.logger.error(f"Error sending email: {str(e)}")
        return False

# ============ HEALTH & MONITORING ============

@app.route("/", methods=["GET", "HEAD"])
def health_check():
    return {
        "status": "ok",
        "service": "TSSM Alumni Backend",
        "version": "1.0.0"
    }, 200




@app.route(f'/api/{API_VERSION}/metrics', methods=['GET'])
@admin_required
def get_metrics():
    """Get API metrics (admin only)"""
    try:
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

# ============ EMAIL ANNOUNCEMENT ENDPOINTS ============

@app.route(f'/api/{API_VERSION}/admin/announcements/preview', methods=['POST'])
@admin_required
def preview_announcement_recipients():
    """Preview recipients for bulk email announcement"""
    try:
        data = request.get_json()
        filters = data.get('filters', {})
        
        # Build query based on filters
        query = {'is_verified': True}  # Only send to verified alumni
        
        # Filter by department
        if filters.get('departments') and len(filters['departments']) > 0:
            alumni_query = {'department': {'$in': filters['departments']}}
            matching_alumni = list(alumni_collection.find(alumni_query, {'user_id': 1}))
            user_ids = [a['user_id'] for a in matching_alumni]
            query['_id'] = {'$in': [ObjectId(uid) for uid in user_ids if uid]}
        
        # Filter by graduation year
        if filters.get('graduation_years') and len(filters['graduation_years']) > 0:
            alumni_query = {'graduation_year': {'$in': filters['graduation_years']}}
            matching_alumni = list(alumni_collection.find(alumni_query, {'user_id': 1}))
            user_ids = [a['user_id'] for a in matching_alumni]
            if '_id' in query:
                # Combine with department filter using intersection
                existing_ids = query['_id']['$in']
                user_id_objs = [ObjectId(uid) for uid in user_ids if uid]
                query['_id']['$in'] = [uid for uid in existing_ids if uid in user_id_objs]
            else:
                query['_id'] = {'$in': [ObjectId(uid) for uid in user_ids if uid]}
        
        # Get recipient count and sample
        total_count = db.users.count_documents(query)
        sample_recipients = list(db.users.find(query, {'email': 1, 'full_name': 1, 'username': 1}).limit(10))
        
        return jsonify({
            'recipient_count': total_count,
            'sample_recipients': serialize_doc(sample_recipients)
        }), 200
        
    except Exception as e:
        app.logger.error(f"Preview announcement error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/admin/announcements/send', methods=['POST'])
@admin_required
@limiter.exempt
def send_announcement():
    """Send bulk email announcement"""
    try:
        data = request.get_json()
        subject = data.get('subject')
        message = data.get('message')
        filters = data.get('filters', {})
        
        if not subject or not message:
            return jsonify({'error': 'Subject and message are required'}), 400
        
        # Build query based on filters (same logic as preview)
        query = {'is_verified': True}
        
        if filters.get('departments') and len(filters['departments']) > 0:
            alumni_query = {'department': {'$in': filters['departments']}}
            matching_alumni = list(alumni_collection.find(alumni_query, {'user_id': 1}))
            user_ids = [a['user_id'] for a in matching_alumni]
            query['_id'] = {'$in': [ObjectId(uid) for uid in user_ids if uid]}
        
        if filters.get('graduation_years') and len(filters['graduation_years']) > 0:
            alumni_query = {'graduation_year': {'$in': filters['graduation_years']}}
            matching_alumni = list(alumni_collection.find(alumni_query, {'user_id': 1}))
            user_ids = [a['user_id'] for a in matching_alumni]
            if '_id' in query:
                existing_ids = query['_id']['$in']
                user_id_objs = [ObjectId(uid) for uid in user_ids if uid]
                query['_id']['$in'] = [uid for uid in existing_ids if uid in user_id_objs]
            else:
                query['_id'] = {'$in': [ObjectId(uid) for uid in user_ids if uid]}
        
        # Get all recipients
        recipients = list(db.users.find(query, {'email': 1, 'full_name': 1}))
        recipient_emails = [r['email'] for r in recipients]
        
        if not recipients:
            return jsonify({'error': 'No recipients found matching filters'}), 400
        
        # Get current admin user
        current_user_id = get_jwt_identity()
        admin_user = db.users.find_one({'_id': ObjectId(current_user_id)})
        
        # Create announcement record
        announcement = {
            'subject': subject,
            'message': message,
            'filters': filters,
            'recipient_count': len(recipients),
            'recipients': recipient_emails,
            'sent_by': current_user_id,
            'sent_by_name': admin_user.get('username', 'Admin'),
            'sent_at': datetime.now(timezone.utc),
            'status': 'queued',
            'delivery_stats': {
                'total': len(recipients),
                'sent': 0,
                'failed': 0,
                'failed_emails': []
            },
            'created_at': datetime.now(timezone.utc)
        }
        
        result = email_announcements_collection.insert_one(announcement)
        announcement_id = str(result.inserted_id)
        
        # Send emails in background
        def send_batch_emails():
            """Background task to send emails in batches"""
            try:
                # Update status to sending
                email_announcements_collection.update_one(
                    {'_id': ObjectId(announcement_id)},
                    {'$set': {'status': 'sending'}}
                )
                
                sent_count = 0
                failed_count = 0
                failed_emails = []
                batch_size = 50
                
                for i in range(0, len(recipients), batch_size):
                    batch = recipients[i:i + batch_size]
                    
                    for recipient in batch:
                        try:
                            # Create beautiful HTML email
                            logo_url = "https://res.cloudinary.com/dxu2xavnq/image/upload/v1770837812/1637145430bscoer_logo_tg0hjt.webp"
                            
                            # Plain text version
                            text_content = f"""Hello {recipient.get('full_name', 'Alumni')},

New Announcement: {subject}

{message}

Check the alumni portal for more details!

Best regards,
TSSM Alumni Team"""
                            
                            # HTML version with styling
                            html_content = f"""
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f9f9f9; padding: 20px; margin: 0;">
    <div style="max-width: 600px; margin: auto; background-color: #ffffff; border-radius: 10px; padding: 0; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
      
      <!-- Header with Logo -->
      <div style="text-align: center; padding: 30px 20px 20px 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px 10px 0 0;">
        <img src="{logo_url}" alt="TSSM Logo" style="height: 80px; margin-bottom: 15px;">
        <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">TSSM Alumni Portal</h1>
      </div>
      
      <!-- Content Area -->
      <div style="padding: 40px 30px; background-color: #ffffff;">
        <h2 style="color: #333333; margin-top: 0; margin-bottom: 20px; font-size: 22px;">
          📢 {subject}
        </h2>
        
        <div style="color: #555555; line-height: 1.6; font-size: 15px; white-space: pre-wrap;">
{message}
        </div>
        
        <div style="margin-top: 35px; padding-top: 25px; border-top: 2px solid #f0f0f0;">
          <p style="color: #666666; font-size: 14px; margin: 0;">
            Visit the <a href="https://bscoer.vercel.app" style="color: #667eea; text-decoration: none; font-weight: 600;">Alumni Portal</a> for more details.
          </p>
        </div>
      </div>
      
      <!-- Footer -->
      <div style="background-color: #f8f9fa; padding: 25px 30px; text-align: center; border-radius: 0 0 10px 10px; border-top: 1px solid #e9ecef;">
        <p style="font-size: 13px; color: #999999; margin: 0 0 8px 0;">
          Best regards,<br/>
          <strong style="color: #666666;">TSSM Alumni Team</strong>
        </p>
        <p style="font-size: 12px; color: #aaaaaa; margin: 0;">
          © {datetime.now(timezone.utc).year} TSSM Alumni Portal. All rights reserved.
        </p>
      </div>
      
    </div>
  </body>
</html>
"""
                            
                            success = send_email_via_gmail(
                                subject,
                                html_content,  # Send HTML content
                                recipient['email']
                            )
                            if success:
                                sent_count += 1
                            else:
                                failed_count += 1
                                failed_emails.append(recipient['email'])
                        except Exception as e:
                            app.logger.error(f"Failed to send email to {recipient['email']}: {str(e)}")
                            failed_count += 1
                            failed_emails.append(recipient['email'])
                    
                    # Delay between batches to avoid rate limits
                    if i + batch_size < len(recipients):
                        time.sleep(2)
                
                # Update final delivery stats
                email_announcements_collection.update_one(
                    {'_id': ObjectId(announcement_id)},
                    {
                        '$set': {
                            'status': 'sent',
                            'delivery_stats': {
                                'total': len(recipients),
                                'sent': sent_count,
                                'failed': failed_count,
                                'failed_emails': failed_emails
                            }
                        }
                    }
                )
                
                app.logger.info(f"Announcement {announcement_id} sent: {sent_count} succeeded, {failed_count} failed")
                
            except Exception as e:
                app.logger.error(f"Batch email sending error: {str(e)}")
                email_announcements_collection.update_one(
                    {'_id': ObjectId(announcement_id)},
                    {'$set': {'status': 'failed'}}
                )
        
        # Start background thread
        thread = threading.Thread(target=send_batch_emails, daemon=True)
        thread.start()
        
        return jsonify({
            'message': 'Announcement queued for sending',
            'announcement_id': announcement_id,
            'recipient_count': len(recipients)
        }), 201
        
    except Exception as e:
        app.logger.error(f"Send announcement error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/admin/announcements', methods=['GET'])
@admin_required
def get_announcements():
    """Get announcement history"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        skip = (page - 1) * per_page
        
        total = email_announcements_collection.count_documents({})
        announcements = list(email_announcements_collection.find()
                           .sort('sent_at', DESCENDING)
                           .skip(skip)
                           .limit(per_page))
        
        return jsonify({
            'announcements': serialize_doc(announcements),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
        
    except Exception as e:
        app.logger.error(f"Get announcements error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/admin/announcements/<announcement_id>', methods=['GET'])
@admin_required
def get_announcement_details(announcement_id):
    """Get announcement details"""
    try:
        announcement = email_announcements_collection.find_one({'_id': ObjectId(announcement_id)})
        
        if not announcement:
            return jsonify({'error': 'Announcement not found'}), 404
        
        return jsonify({'announcement': serialize_doc(announcement)}), 200
        
    except Exception as e:
        app.logger.error(f"Get announcement details error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============ AUTHENTICATION ENDPOINTS ============

# ============ AUTHENTICATION ENDPOINTS ============

@app.route(f'/api/{API_VERSION}/auth/register', methods=['POST'])
@limiter.exempt
def register():
    """Register a new user - Step 1: Send OTP"""
    try:
        data = request.get_json()
        app.logger.info(f"Registration request received for: {data.get('email')}")
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        phone = data.get('phone')
        graduation_year = data.get('graduation_year')
        department = data.get('department')
        degree_certificate_url = data.get('degree_certificate_url')  # Cloudinary URL
        admin_key = data.get('admin_key', '')

        # Validation
        if not all([username, email, password, full_name]):
            return jsonify({'error': 'Username, email, password, and full name are required'}), 400

        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400

        # Check if username or email already exists in users or temp registrations
        if db.users.find_one({'username': username}):
            return jsonify({'error': 'Username already exists'}), 400
        
        if db.users.find_one({'email': email}):
            return jsonify({'error': 'Email already registered'}), 400
            
        if db.temp_registrations.find_one({'email': email}):
            # Delete old temp registration
            db.temp_registrations.delete_one({'email': email})

        # Generate OTP
        otp = generate_otp()
        
        # Store in temporary registrations
        temp_reg = {
            'username': username,
            'email': email,
            'password': password,  # Will be hashed after verification
            'full_name': full_name,
            'phone': phone,
            'graduation_year': graduation_year,
            'department': department,
            'degree_certificate_url': degree_certificate_url,
            'admin_key': admin_key,
            'otp': otp,
            'created_at': datetime.now(timezone.utc)
        }
        
        db.temp_registrations.insert_one(temp_reg)
        
        # Send OTP email
        email_sent = send_email_async(
            'Email Verification - TSSM Alumni Portal',
            f'''
            <h2>Welcome to TSSM Alumni Portal!</h2>
            <p>Hello <strong>{full_name}</strong>,</p>
            <p>Thank you for registering. Please verify your email address using the code below:</p>
            <div style="background: #667eea; color: white; padding: 20px; text-align: center; border-radius: 10px; margin: 20px 0;">
                <h1 style="margin: 0; font-size: 36px; letter-spacing: 5px;">{otp}</h1>
            </div>
            <p>This code will expire in 15 minutes.</p>
            <p>After verification, your registration will be reviewed by our admin team.</p>
            <p>If you didn't request this, please ignore this email.</p>
            ''',
            email
        )
        
        if not email_sent:
            app.logger.warning(f"Failed to send OTP email to {email}")
        
        app.logger.info(f"Registration OTP sent to: {email}")
        
        return jsonify({
            'message': 'Registration initiated. Please check your email for OTP verification code.',
            'email': email
        }), 201

    except Exception as e:
        app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/auth/verify-otp', methods=['POST'])
@limiter.exempt
def verify_otp():
    """Verify OTP and create user account (pending admin approval)"""
    try:
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')

        if not email or not otp:
            return jsonify({'error': 'Email and OTP are required'}), 400

        temp_reg = db.temp_registrations.find_one({'email': email})
        
        if not temp_reg:
            return jsonify({'error': 'Registration not found or already completed'}), 404

        # Check OTP expiry (15 minutes)
        created_at = temp_reg.get('created_at')
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if created_at and datetime.now(timezone.utc) - created_at > timedelta(minutes=15):
            db.temp_registrations.delete_one({'email': email})
            return jsonify({'error': 'OTP expired. Please register again'}), 400

        if temp_reg['otp'] != otp:
            return jsonify({'error': 'Invalid OTP'}), 400

        # Create user account with pending approval status
        is_admin = temp_reg.get('admin_key') == os.getenv('ADMIN_KEY')
        
        user_data = {
            'username': temp_reg['username'],
            'password': generate_password_hash(temp_reg['password']),
            'email': temp_reg['email'],
            'full_name': temp_reg.get('full_name'),
            'phone': temp_reg.get('phone'),
            'is_admin': is_admin,
            'is_verified': True,  # Email verified
            'approval_status': 'approved' if is_admin else 'pending',  # Admins auto-approved
            'created_at': datetime.now(timezone.utc),
            'profile_image': None,
            'bio': '',
            'is_active': True
        }
        
        result = db.users.insert_one(user_data)
        user_id = str(result.inserted_id)
        
        # Create alumni profile with registration data
        alumni_data = {
            'user_id': user_id,
            'full_name': temp_reg.get('full_name'),
            'email': temp_reg['email'],
            'phone': temp_reg.get('phone'),
            'graduation_year': temp_reg.get('graduation_year'),
            'department': temp_reg.get('department'),
            'degree_certificate_url': temp_reg.get('degree_certificate_url'),
            'current_company': '',
            'current_position': '',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'is_verified': False  # Will be verified by admin
        }
        
        alumni_collection.insert_one(alumni_data)
        
        # Delete temporary registration
        db.temp_registrations.delete_one({'email': email})
        
        app.logger.info(f"User registered successfully: {email}, Approval status: {user_data['approval_status']}")
        
        # If pending approval, don't return tokens
        if user_data['approval_status'] == 'pending':
            return jsonify({
                'message': 'Registration successful! Your account is pending admin approval. You will receive an email once approved.',
                'approval_status': 'pending',
                'email': email
            }), 201
        
        # For admins, create and return tokens
        access_token = create_access_token(identity=user_id)
        refresh_token = create_refresh_token(identity=user_id)
        
        return jsonify({
            'message': 'Registration successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user_id,
                'username': temp_reg['username'],
                'email': temp_reg['email'],
                'is_admin': is_admin,
                'approval_status': 'approved'
            }
        }), 201

    except Exception as e:
        app.logger.error(f"OTP verification error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/auth/resend-otp', methods=['POST'])
@limiter.exempt
def resend_otp():
    """Resend OTP for email verification"""
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        temp_reg = db.temp_registrations.find_one({'email': email})
        
        if not temp_reg:
            return jsonify({'error': 'Registration not found'}), 404

        otp = generate_otp()
        
        db.temp_registrations.update_one(
            {'email': email},
            {'$set': {'otp': otp, 'created_at': datetime.now(timezone.utc)}}
        )
        
        send_email_async(
            'Email Verification - Alumni Portal',
            f'<p>Your new verification code is: <strong style="font-size: 24px; color: #667eea;">{otp}</strong></p><p>This code will expire in 15 minutes.</p>',
            email
        )
        
        return jsonify({'message': 'OTP resent successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/auth/login', methods=['POST'])
@limiter.limit("10 per hour")
def login():
    """Login user with email or username"""
    try:
        data = request.get_json()
        identifier = data.get('email')  # Can be email or username
        password = data.get('password')

        if not identifier or not password:
            return jsonify({'error': 'Email/Username and password are required'}), 400

        # Try to find user by email or username
        user = db.users.find_one({
            '$or': [
                {'email': identifier},
                {'username': identifier}
            ]
        })
        
        if not user or not check_password_hash(user['password'], password):
            app.logger.warning(f"Failed login attempt for identifier: {identifier}")
            return jsonify({'error': 'Invalid email/username or password'}), 401

        if not user.get('is_active', True):
            return jsonify({'error': 'Account is deactivated'}), 403
        
        # Check approval status
        approval_status = user.get('approval_status', 'approved')
        if approval_status == 'pending':
            return jsonify({
                'error': 'Your account is pending admin approval. Please wait for approval email.',
                'approval_status': 'pending'
            }), 403
        elif approval_status == 'rejected':
            return jsonify({
                'error': 'Your registration has been rejected. Please contact support.',
                'approval_status': 'rejected'
            }), 403

        # Update last login
        db.users.update_one(
            {'_id': user['_id']},
            {'$set': {'last_login': datetime.now(timezone.utc)}}
        )

        # Create tokens
        access_token = create_access_token(identity=str(user['_id']))
        refresh_token = create_refresh_token(identity=str(user['_id']))

        # Check if alumni profile exists
        alumni_profile = alumni_collection.find_one({'user_id': str(user['_id'])})

        app.logger.info(f"User logged in: {identifier}")

        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': str(user['_id']),
                'username': user['username'],
                'email': user['email'],
                'is_admin': user.get('is_admin', False),
                'profile_image': user.get('profile_image'),
                'bio': user.get('bio', ''),
                'has_alumni_profile': alumni_profile is not None
            }
        }), 200

    except Exception as e:
        app.logger.error(f"Login error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    current_user_id = get_jwt_identity()
    access_token = create_access_token(identity=current_user_id)
    return jsonify({'access_token': access_token}), 200

@app.route(f'/api/{API_VERSION}/auth/me', methods=['GET'])
@jwt_required()
@cache.cached(timeout=60, key_prefix=lambda: f"user_{get_jwt_identity()}")
def get_current_user_info():
    """Get current user information"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.pop('password', None)
        
        # Get alumni profile if exists (convert string _id to ObjectId for query)
        user_object_id = ObjectId(user['_id'])
        alumni_profile = alumni_collection.find_one({'user_id': user_object_id})
        if alumni_profile:
            user['alumni_profile'] = serialize_doc(alumni_profile)
        
        return jsonify({'user': user}), 200

    except Exception as e:
        import traceback
        app.logger.error(f"Error in get_current_user_info: {str(e)}")
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user"""
    app.logger.info(f"User logged out: {get_jwt_identity()}")
    return jsonify({'message': 'Logout successful'}), 200

# ============ NEWS ENDPOINTS ============

@app.route(f'/api/{API_VERSION}/categories', methods=['GET'])
@cache.cached(timeout=1800)  # Cache for 30 minutes (increased from 5)
def list_categories():
    """Get list of categories - Heavily cached for performance"""
    if news_collection is None:
        return jsonify({'error': 'Database unavailable', 'categories': []}), 503
    try:
        categories = news_collection.distinct(
            'category',
            {'category': {'$exists': True, '$ne': None, '$ne': ''}}
        )
        categories = sorted([c for c in categories if isinstance(c, str)])
        return jsonify({'categories': categories}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/tags', methods=['GET'])
@cache.cached(timeout=1800)  # Cache for 30 minutes (increased from 5)
def list_tags():
    """Get list of tags - Heavily cached for performance"""
    if news_collection is None:
        return jsonify({'error': 'Database unavailable', 'tags': []}), 503
    try:
        tags = news_collection.distinct(
            'tags',
            {'tags': {'$exists': True, '$ne': None}}
        )
        tags = sorted([t for t in tags if isinstance(t, str) and t.strip()])
        return jsonify({'tags': tags}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/news', methods=['GET'])
@cache.cached(timeout=180, query_string=True)  # Cache for 3 minutes with query parameters
def list_news():
    """Get list of news articles - Optimized for high traffic"""
    if news_collection is None:
        return jsonify({'error': 'Database unavailable', 'articles': []}), 503
    try:
        page = max(int(request.args.get('page', 1)), 1)
        per_page = min(max(int(request.args.get('per_page', 10)), 1), 50)

        status = request.args.get('status', 'approved')
        category = request.args.get('category')
        tag = request.args.get('tag')
        search = request.args.get('search')

        query = {}
        if status and status != 'all':
            query['status'] = status
        if category:
            query['category'] = category
        if tag:
            query['tags'] = tag
        if search:
            query['$text'] = {'$search': search}

        # Optimized: Use count_documents with hint for indexed fields
        total = news_collection.count_documents(query)
        
        # Keep content in feed response so frontend can render inline Read more/Show less
        articles = list(
            news_collection.find(query)
            .sort('submitted_at', DESCENDING)
            .skip((page - 1) * per_page)
            .limit(per_page)
            .hint([('submitted_at', DESCENDING)])  # Use index hint for better performance
        )

        # Batch enrichment for better performance
        for article in articles:
            enrich_article_submitter(article)
            # Ensure created_at exists for frontend compatibility
            if 'created_at' not in article and 'submitted_at' in article:
                article['created_at'] = article['submitted_at']

        return jsonify({
            'articles': serialize_doc(articles),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        app.logger.error(f"Error listing news: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/news/mine', methods=['GET'])
@jwt_required()
def list_my_news():
    """Get current user's news articles"""
    try:
        current_user_id = get_jwt_identity()
        page = max(int(request.args.get('page', 1)), 1)
        per_page = min(max(int(request.args.get('per_page', 10)), 1), 50)

        query = {'submitter_id': current_user_id}
        total = news_collection.count_documents(query)
        articles = list(
            news_collection.find(query)
            .sort('submitted_at', DESCENDING)
            .skip((page - 1) * per_page)
            .limit(per_page)
        )
        
        # Ensure created_at exists for frontend compatibility
        for article in articles:
            if 'created_at' not in article and 'submitted_at' in article:
                article['created_at'] = article['submitted_at']

        return jsonify({
            'articles': serialize_doc(articles),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/news/image', methods=['POST'])
@jwt_required()
def upload_news_image():
    """Upload news image and return the URL"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'Image file is required'}), 400

        image_file = request.files['image']
        if not image_file or image_file.filename == '':
            return jsonify({'error': 'Image file is required'}), 400

        upload_result = cloudinary.uploader.upload(
            image_file,
            folder='news_images',
            resource_type='image'
        )

        image_url = upload_result.get('secure_url')
        if not image_url:
            return jsonify({'error': 'Image upload failed'}), 500

        return jsonify({'image_url': image_url}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/upload/degree-certificate', methods=['POST'])
@limiter.limit("10 per hour")
def upload_degree_certificate():
    """Upload degree certificate (for registration) and return the URL"""
    try:
        if 'certificate' not in request.files:
            return jsonify({'error': 'Certificate file is required'}), 400

        cert_file = request.files['certificate']
        if not cert_file or cert_file.filename == '':
            return jsonify({'error': 'Certificate file is required'}), 400

        # Validate file type (images and PDFs)
        allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf'}
        file_ext = cert_file.filename.rsplit('.', 1)[1].lower() if '.' in cert_file.filename else ''
        
        if file_ext not in allowed_extensions:
            return jsonify({'error': 'Only images (PNG, JPG, JPEG) and PDF files are allowed'}), 400

        # Determine resource type
        resource_type = 'image' if file_ext in {'png', 'jpg', 'jpeg'} else 'raw'

        upload_result = cloudinary.uploader.upload(
            cert_file,
            folder='degree_certificates',
            resource_type=resource_type
        )

        cert_url = upload_result.get('secure_url')
        if not cert_url:
            return jsonify({'error': 'Certificate upload failed'}), 500

        return jsonify({
            'certificate_url': cert_url,
            'public_id': upload_result.get('public_id')
        }), 200
    except Exception as e:
        app.logger.error(f"Certificate upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/news/<news_id>', methods=['GET'])
def get_news(news_id):
    """Get a single news article (approved only)"""
    try:
        try:
            obj_id = ObjectId(news_id)
        except Exception:
            return jsonify({'error': 'Invalid news id'}), 400

        article = news_collection.find_one({'_id': obj_id})
        if not article:
            return jsonify({'error': 'Article not found'}), 404

        if article.get('status', 'pending') != 'approved':
            return jsonify({'error': 'Article not found'}), 404

        news_collection.update_one({'_id': obj_id}, {'$inc': {'views': 1}})

        # Add submitter information
        enrich_article_submitter(article)
        
        # Ensure created_at exists for frontend compatibility
        if 'created_at' not in article and 'submitted_at' in article:
            article['created_at'] = article['submitted_at']

        return jsonify({'article': serialize_doc(article)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/news', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def submit_news():
    """Submit a news article"""
    try:
        data = request.get_json() or {}
        title = data.get('title')
        content = data.get('content')
        category = data.get('category')

        if not title or not content or not category:
            return jsonify({'error': 'Title, content, and category are required'}), 400

        tags = data.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]
        if not isinstance(tags, list):
            tags = []

        now = datetime.now(timezone.utc)
        article = {
            'title': title,
            'content': content,
            'summary': data.get('summary', ''),
            'category': category,
            'tags': tags,
            'image_url': data.get('image_url'),
            'status': 'pending',
            'submitter_id': get_jwt_identity(),
            'submitted_at': now,
            'created_at': now,
            'updated_at': now,
            'views': 0
        }

        result = news_collection.insert_one(article)
        cache.clear()

        actor = db.users.find_one({'_id': ObjectId(article['submitter_id'])})
        actor_username = (actor or {}).get('username') if actor else None
        mention_text = f"{title}\n{content}\n{article.get('summary', '')}"
        create_mention_notifications(
            mention_text,
            article['submitter_id'],
            actor_username,
            'news post',
            result.inserted_id,
            title
        )

        return jsonify({
            'message': 'Article submitted successfully',
            'article_id': str(result.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/news/<news_id>', methods=['PUT'])
@jwt_required()
def update_news(news_id):
    """Update a news article"""
    try:
        try:
            obj_id = ObjectId(news_id)
        except Exception:
            return jsonify({'error': 'Invalid news id'}), 400

        article = news_collection.find_one({'_id': obj_id})
        if not article:
            return jsonify({'error': 'Article not found'}), 404

        current_user_id = get_jwt_identity()
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        is_admin = user.get('is_admin', False) if user else False

        if not is_admin and article.get('submitter_id') != current_user_id:
            return jsonify({'error': 'Not authorized to edit this article'}), 403

        data = request.get_json() or {}
        update_fields = {}

        for field in ['title', 'content', 'summary', 'category', 'image_url']:
            if field in data:
                update_fields[field] = data[field]

        if 'tags' in data:
            tags = data.get('tags', [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(',') if t.strip()]
            update_fields['tags'] = tags if isinstance(tags, list) else []

        if 'status' in data and is_admin:
            update_fields['status'] = data['status']

        if not update_fields:
            return jsonify({'error': 'No valid fields provided'}), 400

        update_fields['updated_at'] = datetime.now(timezone.utc)

        news_collection.update_one({'_id': obj_id}, {'$set': update_fields})
        cache.clear()

        actor_username = (user or {}).get('username') if user else None
        mention_text = "\n".join([
            str(update_fields.get('title', article.get('title', ''))),
            str(update_fields.get('content', article.get('content', ''))),
            str(update_fields.get('summary', article.get('summary', '')))
        ])
        create_mention_notifications(
            mention_text,
            current_user_id,
            actor_username,
            'news post',
            obj_id,
            str(update_fields.get('title', article.get('title', '')))
        )

        return jsonify({'message': 'Article updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/news/<news_id>', methods=['DELETE'])
@jwt_required()
def delete_news(news_id):
    """Delete a news article"""
    try:
        try:
            obj_id = ObjectId(news_id)
        except Exception:
            return jsonify({'error': 'Invalid news id'}), 400

        article = news_collection.find_one({'_id': obj_id})
        if not article:
            return jsonify({'error': 'Article not found'}), 404

        current_user_id = get_jwt_identity()
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        is_admin = user.get('is_admin', False) if user else False

        if not is_admin and article.get('submitter_id') != current_user_id:
            return jsonify({'error': 'Not authorized to delete this article'}), 403

        news_collection.delete_one({'_id': obj_id})
        cache.clear()

        return jsonify({'message': 'Article deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ REACTIONS & ENGAGEMENT ENDPOINTS ============

@app.route(f'/api/{API_VERSION}/articles/<article_id>/reactions', methods=['POST'])
@jwt_required()
def toggle_article_reaction(article_id):
    """Toggle a reaction on an article (like, love, celebrate)"""
    try:
        try:
            obj_id = ObjectId(article_id)
        except Exception:
            return jsonify({'error': 'Invalid article id'}), 400
        
        data = request.get_json() or {}
        reaction_type = data.get('type')  # 'like', 'love', 'celebrate'
        
        if reaction_type not in ['like', 'love', 'celebrate']:
            return jsonify({'error': 'Invalid reaction type. Must be: like, love, or celebrate'}), 400
        
        article = news_collection.find_one({'_id': obj_id})
        if not article:
            return jsonify({'error': 'Article not found'}), 404
        
        current_user_id = get_jwt_identity()
        
        # Initialize reactions if not exists
        if 'reactions' not in article:
            article['reactions'] = {'like': [], 'love': [], 'celebrate': []}
        
        # Check if user already reacted with this type
        user_reactions = article.get('reactions', {})
        reaction_list = user_reactions.get(reaction_type, [])
        
        if current_user_id in reaction_list:
            # Remove reaction
            news_collection.update_one(
                {'_id': obj_id},
                {
                    '$pull': {f'reactions.{reaction_type}': current_user_id},
                    '$inc': {'reaction_count': -1}
                }
            )
            action = 'removed'
        else:
            # Add reaction (remove from other types first)
            for rtype in ['like', 'love', 'celebrate']:
                if rtype != reaction_type and current_user_id in user_reactions.get(rtype, []):
                    news_collection.update_one(
                        {'_id': obj_id},
                        {'$pull': {f'reactions.{rtype}': current_user_id}}
                    )
            
            news_collection.update_one(
                {'_id': obj_id},
                {
                    '$addToSet': {f'reactions.{reaction_type}': current_user_id},
                    '$inc': {'reaction_count': 1}
                }
            )
            action = 'added'
        
        # Get updated counts
        updated_article = news_collection.find_one({'_id': obj_id}, {'reactions': 1, 'reaction_count': 1})
        reactions = updated_article.get('reactions', {})
        
        cache.clear()
        
        return jsonify({
            'message': f'Reaction {action}',
            'action': action,
            'reactions': {
                'like': len(reactions.get('like', [])),
                'love': len(reactions.get('love', [])),
                'celebrate': len(reactions.get('celebrate', []))
            },
            'total_reactions': updated_article.get('reaction_count', 0),
            'user_reaction': reaction_type if action == 'added' else None
        }), 200
        
    except Exception as e:
        app.logger.error(f"Toggle reaction error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/articles/<article_id>/reactions', methods=['GET'])
def get_article_reactions(article_id):
    """Get reactions for an article"""
    try:
        try:
            obj_id = ObjectId(article_id)
        except Exception:
            return jsonify({'error': 'Invalid article id'}), 400
        
        article = news_collection.find_one({'_id': obj_id}, {'reactions': 1, 'reaction_count': 1})
        if not article:
            return jsonify({'error': 'Article not found'}), 404
        
        reactions = article.get('reactions', {})
        current_user_id = None
        
        try:
            if request.headers.get('Authorization'):
                current_user_id = get_jwt_identity()
        except:
            pass
        
        user_reaction = None
        if current_user_id:
            for rtype in ['like', 'love', 'celebrate']:
                if current_user_id in reactions.get(rtype, []):
                    user_reaction = rtype
                    break
        
        return jsonify({
            'reactions': {
                'like': len(reactions.get('like', [])),
                'love': len(reactions.get('love', [])),
                'celebrate': len(reactions.get('celebrate', []))
            },
            'total_reactions': article.get('reaction_count', 0),
            'user_reaction': user_reaction
        }), 200
        
    except Exception as e:
        app.logger.error(f"Get reactions error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/articles/<article_id>/bookmark', methods=['POST'])
@jwt_required()
def toggle_bookmark(article_id):
    """Toggle bookmark on an article"""
    try:
        try:
            obj_id = ObjectId(article_id)
        except Exception:
            return jsonify({'error': 'Invalid article id'}), 400
        
        article = news_collection.find_one({'_id': obj_id})
        if not article:
            return jsonify({'error': 'Article not found'}), 404
        
        current_user_id = get_jwt_identity()
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        bookmarked_articles = user.get('bookmarked_articles', [])
        
        # Convert article_id string to ObjectId for consistent comparison
        if obj_id in bookmarked_articles:
            # Remove bookmark
            db.users.update_one(
                {'_id': ObjectId(current_user_id)},
                {'$pull': {'bookmarked_articles': obj_id}}
            )
            action = 'removed'
        else:
            # Add bookmark
            db.users.update_one(
                {'_id': ObjectId(current_user_id)},
                {'$addToSet': {'bookmarked_articles': obj_id}}
            )
            action = 'added'
        
        return jsonify({
            'message': f'Bookmark {action}',
            'action': action,
            'is_bookmarked': action == 'added'
        }), 200
        
    except Exception as e:
        app.logger.error(f"Toggle bookmark error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/user/bookmarks', methods=['GET'])
@jwt_required()
def get_bookmarked_articles():
    """Get user's bookmarked articles"""
    try:
        current_user_id = get_jwt_identity()
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        bookmarked_article_ids = user.get('bookmarked_articles', [])
        
        if not bookmarked_article_ids:
            return jsonify({
                'bookmarks': [],
                'total': 0
            }), 200
        
        # Get articles
        articles = list(news_collection.find({
            '_id': {'$in': bookmarked_article_ids},
            'status': 'approved'
        }).sort('submitted_at', DESCENDING))
        
        # Enrich with submitter info
        for article in articles:
            enrich_article_submitter(article)
        
        return jsonify({
            'bookmarks': serialize_doc(articles),
            'total': len(articles)
        }), 200
        
    except Exception as e:
        app.logger.error(f"Get bookmarks error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/articles/<article_id>/view', methods=['POST'])
def track_article_view(article_id):
    """Track article view (increment view count and unique viewers)"""
    try:
        try:
            obj_id = ObjectId(article_id)
        except Exception:
            return jsonify({'error': 'Invalid article id'}), 400
        
        article = news_collection.find_one({'_id': obj_id})
        if not article:
            return jsonify({'error': 'Article not found'}), 404
        
        # Get user ID if authenticated (optional)
        user_id = None
        try:
            if request.headers.get('Authorization'):
                user_id = get_jwt_identity()
        except:
            pass
        
        # Initialize views and unique_viewers if not exists
        update_query = {'$inc': {'views': 1}}
        
        if user_id:
            # Add to unique viewers if not already there
            unique_viewers = article.get('unique_viewers', [])
            if user_id not in unique_viewers:
                update_query['$addToSet'] = {'unique_viewers': user_id}
        
        news_collection.update_one({'_id': obj_id}, update_query)
        
        # Get updated view count
        updated_article = news_collection.find_one({'_id': obj_id}, {'views': 1, 'unique_viewers': 1})
        
        return jsonify({
            'message': 'View tracked',
            'views': updated_article.get('views', 0),
            'unique_visitors': len(updated_article.get('unique_viewers', []))
        }), 200
        
    except Exception as e:
        app.logger.error(f"Track view error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============ ALUMNI PROFILE ENDPOINTS ============

@app.route(f'/api/{API_VERSION}/alumni/profile', methods=['POST'])
@jwt_required()
@limiter.limit("5 per hour")
def create_alumni_profile():
    """Create alumni profile"""
    try:
        current_user_id = get_jwt_identity()
        
        # Check if profile already exists (handle historical ObjectId/string user_id formats)
        alumni_user_id_query = {'$in': [current_user_id]}
        try:
            alumni_user_id_query['$in'].append(ObjectId(current_user_id))
        except Exception:
            pass

        if alumni_collection.find_one({'user_id': alumni_user_id_query}):
            return jsonify({'error': 'Alumni profile already exists'}), 400
        
        data = request.get_json()
        
        alumni_data = {
            'user_id': current_user_id,
            'full_name': data.get('full_name'),
            'graduation_year': data.get('graduation_year'),
            'batch': data.get('batch'),
            'department': data.get('department'),
            'course': data.get('course'),
            'enrollment_number': data.get('enrollment_number'),
            'current_company': data.get('current_company'),
            'current_position': data.get('current_position'),
            'current_location': data.get('current_location'),
            'industry': data.get('industry'),
            'linkedin_url': data.get('linkedin_url'),
            'phone': data.get('phone'),
            'achievements': data.get('achievements', []),
            'skills': data.get('skills', []),
            'interests': data.get('interests', []),
            'willing_to_mentor': data.get('willing_to_mentor', False),
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'is_verified': False
        }
        
        result = alumni_collection.insert_one(alumni_data)
        
        app.logger.info(f"Alumni profile created for user: {current_user_id}")
        
        return jsonify({
            'message': 'Alumni profile created successfully',
            'profile_id': str(result.inserted_id)
        }), 201

    except Exception as e:
        app.logger.error(f"Error creating alumni profile: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/alumni/profile', methods=['GET'])
@jwt_required()
def get_my_alumni_profile():
    """Get current user's alumni profile"""
    try:
        current_user_id = get_jwt_identity()
        
        alumni_user_id_query = {'$in': [current_user_id]}
        try:
            alumni_user_id_query['$in'].append(ObjectId(current_user_id))
        except Exception:
            pass

        alumni_profile = alumni_collection.find_one({'user_id': alumni_user_id_query})
        
        if not alumni_profile:
            return jsonify({'error': 'Alumni profile not found'}), 404
        
        return jsonify({'profile': serialize_doc(alumni_profile)}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/alumni/profile', methods=['PUT'])
@jwt_required()
def update_alumni_profile():
    """Update alumni profile"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Remove fields that shouldn't be updated via this endpoint
        data.pop('user_id', None)
        data.pop('created_at', None)
        data.pop('is_verified', None)
        
        # Remove deprecated privacy field
        data.pop('is_private_profile', None)
        
        data['updated_at'] = datetime.now(timezone.utc)
        
        alumni_user_id_query = {'$in': [current_user_id]}
        try:
            alumni_user_id_query['$in'].append(ObjectId(current_user_id))
        except Exception:
            pass

        result = alumni_collection.update_one(
            {'user_id': alumni_user_id_query},
            {'$set': data}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'Alumni profile not found'}), 404
        
        # Clear cache
        cache.delete(f"user_{current_user_id}")
        cache.clear()
        
        return jsonify({'message': 'Profile updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/alumni/directory', methods=['GET'])
@jwt_required()
@cache.cached(timeout=300, query_string=True)
def get_alumni_directory():
    """Get alumni directory with filters"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        graduation_year = request.args.get('graduation_year')
        department = request.args.get('department')
        batch = request.args.get('batch')
        company = request.args.get('company')
        search = request.args.get('search')
        
        query = {}
        
        if graduation_year:
            query['graduation_year'] = int(graduation_year)
        if department:
            query['department'] = {'$regex': department, '$options': 'i'}
        if batch:
            query['batch'] = batch
        if company:
            query['current_company'] = {'$regex': company, '$options': 'i'}
        if search:
            query['$or'] = [
                {'full_name': {'$regex': search, '$options': 'i'}},
                {'current_company': {'$regex': search, '$options': 'i'}},
                {'current_position': {'$regex': search, '$options': 'i'}}
            ]
        
        total = alumni_collection.count_documents(query)
        
        alumni = list(alumni_collection.find(query)
                     .sort('graduation_year', DESCENDING)
                     .skip((page - 1) * per_page)
                     .limit(per_page))
        
        # Add user information
        for alum in alumni:
            user = None
            try:
                user = db.users.find_one({'_id': ObjectId(alum['user_id'])})
            except Exception:
                user = None
            if user:
                alum['username'] = user.get('username')
                alum['profile_image'] = user.get('profile_image')
                alum['is_admin'] = user.get('is_admin', False)
                alum['bio'] = user.get('bio', '')
        
        return jsonify({
            'alumni': serialize_doc(alumni),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/alumni/<alumni_id>', methods=['GET'])
@jwt_required()
def get_alumni_profile(alumni_id):
    """Get specific alumni profile"""
    try:
        alumni = alumni_collection.find_one({'_id': ObjectId(alumni_id)})
        
        if not alumni:
            return jsonify({'error': 'Alumni not found'}), 404
        
        # Get user information
        user = None
        try:
            user = db.users.find_one({'_id': ObjectId(alumni['user_id'])})
        except Exception:
            user = None
        if user:
            alumni['username'] = user.get('username')
            alumni['profile_image'] = user.get('profile_image')
            alumni['bio'] = user.get('bio')
        
        return jsonify({'alumni': serialize_doc(alumni)}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ EVENTS ENDPOINTS ============

@app.route(f'/api/{API_VERSION}/events', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def get_events():
    """Get all events"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        event_type = request.args.get('type')
        upcoming = request.args.get('upcoming', 'true').lower() == 'true'
        
        query = {}
        
        if event_type:
            query['event_type'] = event_type
        
        if upcoming:
            query['event_date'] = {'$gte': datetime.now(timezone.utc)}
        
        total = events_collection.count_documents(query)
        
        events = list(events_collection.find(query)
                     .sort('event_date', ASCENDING if upcoming else DESCENDING)
                     .skip((page - 1) * per_page)
                     .limit(per_page))
        
        return jsonify({
            'events': serialize_doc(events),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/events', methods=['POST'])
@jwt_required()
@alumni_required
def create_event():
    """Create new event (alumni only)"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        event_data = {
            'title': data.get('title'),
            'description': data.get('description'),
            'event_type': data.get('event_type'),  # reunion, webinar, workshop, etc.
            'event_date': datetime.fromisoformat(data.get('event_date')),
            'event_time': data.get('event_time'),
            'location': data.get('location'),
            'is_online': data.get('is_online', False),
            'meeting_link': data.get('meeting_link'),
            'organizer_id': current_user_id,
            'max_participants': data.get('max_participants'),
            'registration_deadline': datetime.fromisoformat(data.get('registration_deadline')) if data.get('registration_deadline') else None,
            'status': 'pending',  # pending, approved, cancelled
            'attendees': [],
            'created_at': datetime.now(timezone.utc)
        }
        
        result = events_collection.insert_one(event_data)
        
        cache.clear()
        
        return jsonify({
            'message': 'Event created successfully',
            'event_id': str(result.inserted_id)
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/events/<event_id>/register', methods=['POST'])
@jwt_required()
@alumni_required
def register_for_event(event_id):
    """Register for an event"""
    try:
        current_user_id = get_jwt_identity()
        
        event = events_collection.find_one({'_id': ObjectId(event_id)})
        
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        # Check if already registered
        if current_user_id in event.get('attendees', []):
            return jsonify({'error': 'Already registered for this event'}), 400
        
        # Check max participants
        if event.get('max_participants'):
            if len(event.get('attendees', [])) >= event['max_participants']:
                return jsonify({'error': 'Event is full'}), 400
        
        # Register user
        events_collection.update_one(
            {'_id': ObjectId(event_id)},
            {'$push': {'attendees': current_user_id}}
        )
        
        cache.clear()
        
        return jsonify({'message': 'Successfully registered for event'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ JOBS ENDPOINTS ============

@app.route(f'/api/{API_VERSION}/jobs', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def get_jobs():
    """Get job postings"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        job_type = request.args.get('job_type')
        location = request.args.get('location')
        company = request.args.get('company')
        
        query = {'status': 'active'}
        
        if job_type:
            query['job_type'] = job_type
        if location:
            query['location'] = {'$regex': location, '$options': 'i'}
        if company:
            query['company'] = {'$regex': company, '$options': 'i'}
        
        total = jobs_collection.count_documents(query)
        
        jobs = list(jobs_collection.find(query)
                   .sort('posted_at', DESCENDING)
                   .skip((page - 1) * per_page)
                   .limit(per_page))
        
        return jsonify({
            'jobs': serialize_doc(jobs),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route(f'/api/{API_VERSION}/jobs', methods=['POST'])
@jwt_required()
@alumni_required
def post_job():
    """Post a new job (alumni only)"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        job_data = {
            'title': data.get('title'),
            'company': data.get('company'),
            'description': data.get('description'),
            'requirements': data.get('requirements', []),
            'job_type': data.get('job_type'),  # full-time, part-time, internship, contract
            'location': data.get('location'),
            'is_remote': data.get('is_remote', False),
            'salary_range': data.get('salary_range'),
            'experience_level': data.get('experience_level'),
            'apply_url': data.get('apply_url'),
            'apply_email': data.get('apply_email'),
            'posted_by': current_user_id,
            'posted_at': datetime.now(timezone.utc),
            'status': 'active',
            'views': 0,
            'applications': 0
        }
        
        result = jobs_collection.insert_one(job_data)
        
        cache.clear()
        
        return jsonify({
            'message': 'Job posted successfully',
            'job_id': str(result.inserted_id)
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ ADMIN NEWS MANAGEMENT ============

@app.route(f'/api/{API_VERSION}/admin/news/pending', methods=['GET'])
@admin_required
def get_pending_news():
    """Get all pending news articles (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        query = {'status': 'pending'}
        total = news_collection.count_documents(query)
        
        articles = list(
            news_collection.find(query)
            .sort('submitted_at', DESCENDING)
            .skip((page - 1) * per_page)
            .limit(per_page)
        )
        
        # Add submitter info
        for article in articles:
            enrich_article_submitter(article, include_email=True)
            # Ensure created_at exists for frontend compatibility
            if 'created_at' not in article and 'submitted_at' in article:
                article['created_at'] = article['submitted_at']
        
        return jsonify({
            'articles': serialize_doc(articles),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/news/<news_id>/approve', methods=['POST'])
@admin_required
def approve_news(news_id):
    """Approve a news article (admin only)"""
    try:
        try:
            obj_id = ObjectId(news_id)
        except Exception:
            return jsonify({'error': 'Invalid news id'}), 400
        
        article = news_collection.find_one({'_id': obj_id})
        if not article:
            return jsonify({'error': 'Article not found'}), 404
        
        news_collection.update_one(
            {'_id': obj_id},
            {'$set': {
                'status': 'approved',
                'approved_at': datetime.now(timezone.utc),
                'approved_by': get_jwt_identity()
            }}
        )
        
        cache.clear()
        
        # Send notification to submitter
        submitter = db.users.find_one({'_id': ObjectId(article.get('submitter_id'))})
        if submitter and submitter.get('email'):
            send_email_async(
                'Your Article Has Been Approved',
                f'<p>Great news! Your article "<strong>{article.get("title")}</strong>" has been approved and is now live.</p>',
                submitter['email']
            )
        
        return jsonify({'message': 'Article approved successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/news/<news_id>/reject', methods=['POST'])
@admin_required
def reject_news(news_id):
    """Reject a news article (admin only)"""
    try:
        try:
            obj_id = ObjectId(news_id)
        except Exception:
            return jsonify({'error': 'Invalid news id'}), 400
        
        data = request.get_json() or {}
        reason = data.get('reason', 'No reason provided')
        
        article = news_collection.find_one({'_id': obj_id})
        if not article:
            return jsonify({'error': 'Article not found'}), 404
        
        news_collection.update_one(
            {'_id': obj_id},
            {'$set': {
                'status': 'rejected',
                'rejected_at': datetime.now(timezone.utc),
                'rejected_by': get_jwt_identity(),
                'rejection_reason': reason
            }}
        )
        
        cache.clear()
        
        # Send notification to submitter
        submitter = db.users.find_one({'_id': ObjectId(article.get('submitter_id'))})
        if submitter and submitter.get('email'):
            send_email_async(
                'Your Article Has Been Rejected',
                f'<p>Your article "<strong>{article.get("title")}</strong>" has been rejected.</p><p><strong>Reason:</strong> {reason}</p>',
                submitter['email']
            )
        
        return jsonify({'message': 'Article rejected successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    """Get all users with filters (admin only) - excludes pending users"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '')
        department = request.args.get('department', '')
        year = request.args.get('year', '')
        
        # Exclude pending users - only show approved/rejected/active users
        query = {'approval_status': {'$ne': 'pending'}}
        
        if search:
            query['$or'] = [
                {'username': {'$regex': search, '$options': 'i'}},
                {'email': {'$regex': search, '$options': 'i'}}
            ]
        
        # Get user IDs based on department/year filters from alumni collection
        if department or year:
            alumni_query = {}
            if department:
                alumni_query['department'] = department
            if year:
                alumni_query['graduation_year'] = int(year)
            
            matching_alumni = list(alumni_collection.find(alumni_query, {'user_id': 1}))
            user_ids = [ObjectId(a['user_id']) for a in matching_alumni if a.get('user_id')]
            
            if user_ids:
                if '$or' in query:
                    # Combine with search query
                    query = {
                        '$and': [
                            {'_id': {'$in': user_ids}},
                            {'approval_status': {'$ne': 'pending'}},
                            {'$or': query['$or']}
                        ]
                    }
                else:
                    query['_id'] = {'$in': user_ids}
            else:
                # No matching alumni found
                return jsonify({
                    'users': [],
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': 0,
                        'pages': 0
                    }
                }), 200
        
        total = db.users.count_documents(query)
        users = list(
            db.users.find(query)
            .sort('created_at', DESCENDING)
            .skip((page - 1) * per_page)
            .limit(per_page)
        )
        
        # Remove passwords and add alumni profile info
        for user in users:
            user.pop('password', None)
            
            # Add alumni profile if exists
            alumni = alumni_collection.find_one({'user_id': str(user['_id'])})
            if alumni:
                user['has_alumni_profile'] = True
                user['graduation_year'] = alumni.get('graduation_year')
                user['department'] = alumni.get('department')
            else:
                user['has_alumni_profile'] = False
        
        return jsonify({
            'users': serialize_doc(users),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete a user (admin only) - cannot delete supreme admin"""
    try:
        try:
            obj_id = ObjectId(user_id)
        except Exception:
            return jsonify({'error': 'Invalid user id'}), 400
        
        # Don't allow deleting yourself
        if str(obj_id) == get_jwt_identity():
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        # Check if target user is supreme admin
        target_user = db.users.find_one({'_id': obj_id})
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        if target_user.get('is_supreme_admin', False):
            return jsonify({'error': 'Cannot delete supreme admin'}), 403
        
        # Delete user
        result = db.users.delete_one({'_id': obj_id})
        if result.deleted_count == 0:
            return jsonify({'error': 'User not found'}), 404
        
        # Delete related data
        alumni_collection.delete_one({'user_id': user_id})
        news_collection.delete_many({'submitter_id': user_id})
        
        cache.clear()
        
        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/users', methods=['POST'])
@admin_required
def create_user_admin():
    """Create a user (admin only)"""
    try:
        data = request.get_json() or {}
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        is_admin = bool(data.get('is_admin', False))

        if not username or not email or not password:
            return jsonify({'error': 'Username, email, and password are required'}), 400

        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400

        if db.users.find_one({'username': username}):
            return jsonify({'error': 'Username already exists'}), 400

        if db.users.find_one({'email': email}):
            return jsonify({'error': 'Email already registered'}), 400

        user_data = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'is_admin': is_admin,
            'is_verified': True,
            'created_at': datetime.now(timezone.utc)
        }

        result = db.users.insert_one(user_data)
        cache.clear()

        return jsonify({
            'message': 'User created successfully',
            'user_id': str(result.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/users/<user_id>/toggle-admin', methods=['PUT'])
@admin_required
def toggle_admin_status(user_id):
    """Toggle admin status for a user - cannot modify supreme admin"""
    try:
        try:
            obj_id = ObjectId(user_id)
        except Exception:
            return jsonify({'error': 'Invalid user id'}), 400
        
        # Get target user
        target_user = db.users.find_one({'_id': obj_id})
        if not target_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Cannot modify supreme admin
        if target_user.get('is_supreme_admin', False):
            return jsonify({'error': 'Cannot modify supreme admin status'}), 403
        
        # Toggle admin status
        new_admin_status = not target_user.get('is_admin', False)
        
        db.users.update_one(
            {'_id': obj_id},
            {'$set': {'is_admin': new_admin_status}}
        )
        
        cache.clear()
        
        return jsonify({
            'message': f'User {"promoted to" if new_admin_status else "demoted from"} admin successfully',
            'is_admin': new_admin_status
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/set-supreme-admin', methods=['POST'])
@admin_required
def set_supreme_admin():
    """Set the current admin as supreme admin (can only be done once)"""
    try:
        current_user_id = get_jwt_identity()
        
        # Check if supreme admin already exists
        existing_supreme = db.users.find_one({'is_supreme_admin': True})
        if existing_supreme:
            return jsonify({'error': 'Supreme admin already exists'}), 400
        
        # Set current user as supreme admin
        db.users.update_one(
            {'_id': ObjectId(current_user_id)},
            {'$set': {'is_supreme_admin': True, 'is_admin': True}}
        )
        
        cache.clear()
        app.logger.info(f"Supreme admin set: {current_user_id}")
        
        return jsonify({'message': 'You are now the supreme admin'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/news', methods=['GET'])
@admin_required
def list_all_news_admin():
    """List all news articles (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')

        query = {}
        if status and status != 'all':
            query['status'] = status

        total = news_collection.count_documents(query)
        articles = list(
            news_collection.find(query)
            .sort('submitted_at', DESCENDING)
            .skip((page - 1) * per_page)
            .limit(per_page)
        )

        for article in articles:
            enrich_article_submitter(article, include_email=True)
            # Ensure created_at exists for frontend compatibility
            if 'created_at' not in article and 'submitted_at' in article:
                article['created_at'] = article['submitted_at']

        return jsonify({
            'articles': serialize_doc(articles),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/news/history', methods=['GET'])
@admin_required
def list_news_history():
    """List approved/rejected news history (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')

        if status and status != 'all':
            query = {'status': status}
        else:
            query = {'status': {'$in': ['approved', 'rejected']}}

        total = news_collection.count_documents(query)
        articles = list(
            news_collection.find(query)
            .sort('updated_at', DESCENDING)
            .skip((page - 1) * per_page)
            .limit(per_page)
        )

        for article in articles:
            enrich_article_submitter(article, include_email=True)
            # Ensure created_at exists for frontend compatibility
            if 'created_at' not in article and 'submitted_at' in article:
                article['created_at'] = article['submitted_at']

        return jsonify({
            'articles': serialize_doc(articles),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/comments', methods=['GET'])
@admin_required
def list_comments_admin():
    """List comments (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        total = comments_collection.count_documents({})
        comments = list(
            comments_collection.find({})
            .sort('created_at', DESCENDING)
            .skip((page - 1) * per_page)
            .limit(per_page)
        )

        for comment in comments:
            user_id = comment.get('user_id')
            if user_id:
                user = db.users.find_one({'_id': ObjectId(user_id)})
                if user:
                    comment['username'] = user.get('username')
                    comment['user_email'] = user.get('email')

            article_id = comment.get('article_id') or comment.get('news_id')
            if article_id:
                try:
                    article = news_collection.find_one({'_id': ObjectId(article_id)})
                except Exception:
                    article = None
                if article:
                    comment['article_title'] = article.get('title')

        return jsonify({
            'comments': serialize_doc(comments),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/comments/<comment_id>', methods=['DELETE'])
@admin_required
def delete_comment_admin(comment_id):
    """Delete a comment (admin only)"""
    try:
        try:
            obj_id = ObjectId(comment_id)
        except Exception:
            return jsonify({'error': 'Invalid comment id'}), 400

        result = comments_collection.delete_one({'_id': obj_id})
        if result.deleted_count == 0:
            return jsonify({'error': 'Comment not found'}), 404

        return jsonify({'message': 'Comment deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/settings', methods=['GET'])
@admin_required
def get_admin_settings():
    """Get admin settings (admin only)"""
    try:
        settings = db.settings.find_one() or {}
        settings.pop('_id', None)
        return jsonify({'settings': settings}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/settings', methods=['PUT'])
@admin_required
def update_admin_settings():
    """Update admin settings (admin only)"""
    try:
        data = request.get_json() or {}
        allowed_fields = {
            'smtp_server',
            'smtp_port',
            'email_notifications',
            'site_name',
            'support_email',
            'maintenance_mode',
            'registration_enabled',
            'comments_enabled',
            'article_approval',
            'comment_approval'
        }
        update_fields = {k: v for k, v in data.items() if k in allowed_fields}

        if not update_fields:
            return jsonify({'error': 'No valid settings provided'}), 400

        db.settings.update_one({}, {'$set': update_fields}, upsert=True)

        return jsonify({'message': 'Settings updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/pending-registrations', methods=['GET'])
@admin_required
def get_pending_registrations():
    """Get all pending user registrations (admin only)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Get users with pending approval
        query = {'approval_status': 'pending'}
        total = db.users.count_documents(query)
        
        pending_users = list(db.users.find(query)
                           .sort('created_at', DESCENDING)
                           .skip((page - 1) * per_page)
                           .limit(per_page))
        
        # Enrich with alumni profile data
        for user in pending_users:
            user_id = str(user['_id'])
            alumni_profile = alumni_collection.find_one({'user_id': user_id})
            if alumni_profile:
                user['alumni_profile'] = serialize_doc(alumni_profile)
        
        return jsonify({
            'pending_registrations': serialize_doc(pending_users),
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }), 200
    except Exception as e:
        app.logger.error(f"Error fetching pending registrations: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/registrations/<user_id>/approve', methods=['POST'])
@admin_required
def approve_registration(user_id):
    """Approve a pending user registration (admin only)"""
    try:
        try:
            obj_id = ObjectId(user_id)
        except Exception:
            return jsonify({'error': 'Invalid user id'}), 400
        
        user = db.users.find_one({'_id': obj_id})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.get('approval_status') != 'pending':
            return jsonify({'error': 'User is not pending approval'}), 400
        
        # Approve user
        db.users.update_one(
            {'_id': obj_id},
            {'$set': {
                'approval_status': 'approved',
                'approved_at': datetime.now(timezone.utc)
            }}
        )
        
        # Send approval email (synchronous to confirm delivery attempt)
        email_subject = 'Registration Approved - TSSM Alumni Portal'
        email_content = f'''
            <h2>Welcome to TSSM Alumni Portal!</h2>
            <p>Dear <strong>{user.get('full_name', user.get('username'))}</strong>,</p>
            <p>Great news! Your registration has been approved by our admin team.</p>
            <p>You can now login to your account and access all features of the Alumni Portal.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="https://bscoer.vercel.app/login" style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 10px; display: inline-block;">Login Now</a>
            </div>
            <p>We're excited to have you as part of our alumni community!</p>
        '''

        email_sent = send_email_via_gmail(email_subject, email_content, user['email'])

        if email_sent:
            app.logger.info(f"User registration approved and email sent: {user['email']}")
            return jsonify({'message': 'Registration approved successfully and email sent'}), 200

        app.logger.warning(f"User approved but approval email could not be sent: {user['email']}")
        return jsonify({
            'message': 'Registration approved successfully',
            'warning': 'Approval email could not be sent. Please verify email service configuration.'
        }), 200
    except Exception as e:
        app.logger.error(f"Error approving registration: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/registrations/<user_id>/reject', methods=['POST'])
@admin_required
def reject_registration(user_id):
    """Reject a pending user registration (admin only)"""
    try:
        try:
            obj_id = ObjectId(user_id)
        except Exception:
            return jsonify({'error': 'Invalid user id'}), 400
        
        data = request.get_json() or {}
        reason = data.get('reason', 'Your registration did not meet our requirements.')
        
        user = db.users.find_one({'_id': obj_id})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.get('approval_status') != 'pending':
            return jsonify({'error': 'User is not pending approval'}), 400
        
        # Reject user
        db.users.update_one(
            {'_id': obj_id},
            {'$set': {
                'approval_status': 'rejected',
                'rejection_reason': reason,
                'rejected_at': datetime.now(timezone.utc)
            }}
        )
        
        # Send rejection email
        send_email_async(
            'Registration Update - TSSM Alumni Portal',
            f'''
            <h2>Registration Update</h2>
            <p>Dear <strong>{user.get('full_name', user.get('username'))}</strong>,</p>
            <p>We regret to inform you that your registration for TSSM Alumni Portal has not been approved at this time.</p>
            <p><strong>Reason:</strong> {reason}</p>
            <p>If you believe this is an error or have questions, please contact our support team.</p>
            <p>Thank you for your interest in TSSM Alumni Portal.</p>
            ''',
            user['email']
        )
        
        app.logger.info(f"User registration rejected: {user['email']}")
        
        return jsonify({'message': 'Registration rejected'}), 200
    except Exception as e:
        app.logger.error(f"Error rejecting registration: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    """Get admin dashboard statistics"""
    try:
        stats = {
            'total_users': db.users.count_documents({}),
            'pending_registrations': db.users.count_documents({'approval_status': 'pending'}),
            'approved_users': db.users.count_documents({'approval_status': 'approved'}),
            'total_alumni': alumni_collection.count_documents({}),
            'total_articles': news_collection.count_documents({}),
            'pending_articles': news_collection.count_documents({'status': 'pending'}),
            'approved_articles': news_collection.count_documents({'status': 'approved'}),
            'rejected_articles': news_collection.count_documents({'status': 'rejected'}),
            'total_events': events_collection.count_documents({}),
            'upcoming_events': events_collection.count_documents({
                'event_date': {'$gte': datetime.now(timezone.utc)}
            }),
            'total_jobs': jobs_collection.count_documents({}),
            'active_jobs': jobs_collection.count_documents({'status': 'active'}),
            'recent_registrations': db.users.count_documents({
                'created_at': {'$gte': datetime.now(timezone.utc) - timedelta(days=7)}
            }),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/users/export', methods=['GET'])
@admin_required
def export_users_csv():
    """Export users data as CSV with filters (admin only) - excludes pending users"""
    try:
        search = request.args.get('search', '')
        department = request.args.get('department', '')
        year = request.args.get('year', '')
        
        # Exclude pending users
        query = {'approval_status': {'$ne': 'pending'}}
        
        if search:
            query['$or'] = [
                {'username': {'$regex': search, '$options': 'i'}},
                {'email': {'$regex': search, '$options': 'i'}}
            ]
        
        # Get user IDs based on department/year filters from alumni collection
        if department or year:
            alumni_query = {}
            if department:
                alumni_query['department'] = department
            if year:
                alumni_query['graduation_year'] = int(year)
            
            matching_alumni = list(alumni_collection.find(alumni_query, {'user_id': 1}))
            user_ids = [ObjectId(a['user_id']) for a in matching_alumni if a.get('user_id')]
            
            if user_ids:
                if '$or' in query:
                    # Combine with search query
                    query = {
                        '$and': [
                            {'_id': {'$in': user_ids}},
                            {'approval_status': {'$ne': 'pending'}},
                            {'$or': query['$or']}
                        ]
                    }
                else:
                    query['_id'] = {'$in': user_ids}
            else:
                # No matching alumni found - return empty CSV
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow([
                    'ID', 'Username', 'Email', 'Full Name', 'Department', 
                    'Graduation Year', 'Phone', 'Role', 'Approval Status', 'Created At'
                ])
                output.seek(0)
                from flask import make_response
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'text/csv; charset=utf-8'
                response.headers['Content-Disposition'] = f'attachment; filename=users_export_{datetime.now(timezone.utc).strftime("%Y-%m-%d")}.csv'
                return response
        
        # Fetch all users
        users = list(db.users.find(query).sort('created_at', DESCENDING))
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'ID', 'Username', 'Email', 'Full Name', 'Department', 
            'Graduation Year', 'Phone', 'Role', 'Approval Status', 'Created At'
        ])
        
        # Write data rows
        for user in users:
            user_id = str(user['_id'])
            
            # Get alumni profile if exists
            alumni = alumni_collection.find_one({'user_id': user_id})
            
            writer.writerow([
                user_id,
                user.get('username', ''),
                user.get('email', ''),
                user.get('full_name', ''),
                alumni.get('department', '') if alumni else '',
                alumni.get('graduation_year', '') if alumni else '',
                alumni.get('phone', '') if alumni else user.get('phone', ''),
                'Admin' if user.get('is_admin', False) else 'User',
                user.get('approval_status', 'approved'),
                user.get('created_at', '').isoformat() if user.get('created_at') else ''
            ])
        
        # Prepare response
        output.seek(0)
        from flask import make_response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        
        # Add filter info to filename
        filename_parts = ['users_export']
        if department:
            filename_parts.append(f'dept_{department}')
        if year:
            filename_parts.append(f'year_{year}')
        filename_parts.append(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        filename = '_'.join(filename_parts) + '.csv'
        
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        app.logger.info(f"Users CSV export requested by admin: {get_jwt_identity()} with filters - dept: {department}, year: {year}")
        
        return response
    except Exception as e:
        app.logger.error(f"Error exporting users CSV: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/alumni/export', methods=['GET'])
@admin_required
def export_alumni_csv():
    """Export all alumni profiles as CSV (admin only)"""
    try:
        graduation_year = request.args.get('graduation_year', type=int)
        department = request.args.get('department')
        
        # Build query
        query = {}
        if graduation_year:
            query['graduation_year'] = graduation_year
        if department:
            query['department'] = {'$regex': department, '$options': 'i'}
        
        # Fetch all alumni
        alumni_list = list(alumni_collection.find(query).sort('created_at', DESCENDING))
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            'ID', 'Full Name', 'Email', 'Phone', 'Department', 
            'Graduation Year', 'Batch', 'Current Company', 'Current Position', 
            'LinkedIn URL', 'Created At'
        ])
        
        # Write data rows
        for alumni in alumni_list:
            user_id = alumni.get('user_id')
            
            # Get user data
            user = None
            if user_id:
                try:
                    user = db.users.find_one({'_id': ObjectId(user_id)})
                except Exception:
                    pass
            
            writer.writerow([
                str(alumni['_id']),
                alumni.get('full_name', ''),
                alumni.get('email', '') or (user.get('email', '') if user else ''),
                alumni.get('phone', ''),
                alumni.get('department', ''),
                alumni.get('graduation_year', ''),
                alumni.get('batch', ''),
                alumni.get('current_company', ''),
                alumni.get('current_position', ''),
                alumni.get('linkedin_url', ''),
                alumni.get('created_at', '').isoformat() if alumni.get('created_at') else ''
            ])
        
        # Prepare response
        output.seek(0)
        from flask import make_response
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=alumni_export_{datetime.now(timezone.utc).strftime("%Y-%m-%d")}.csv'
        
        app.logger.info(f"Alumni CSV export requested by admin: {get_jwt_identity()}")
        
        return response
    except Exception as e:
        app.logger.error(f"Error exporting alumni CSV: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ============ USER PROFILE ENDPOINTS ============

@app.route(f'/api/{API_VERSION}/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user's profile"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.pop('password', None)
        
        # Get user's articles (convert string _id back to ObjectId for query)
        user_object_id = ObjectId(user['_id'])
        articles = list(news_collection.find({'submitter_id': user_object_id}).sort('submitted_at', -1).limit(10))
        user['articles'] = serialize_doc(articles)
        user['articles_count'] = news_collection.count_documents({'submitter_id': user_object_id})
        
        # Get alumni profile (handle historical ObjectId/string user_id formats)
        alumni = alumni_collection.find_one({'user_id': {'$in': [str(user['_id']), user_object_id]}})
        if alumni:
            user['alumni_profile'] = serialize_doc(alumni)
        
        return jsonify({'profile': user}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update user profile"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        update_fields = {}
        if 'bio' in data:
            update_fields['bio'] = data['bio']
        if 'profile_image' in data:
            update_fields['profile_image'] = data['profile_image']
        
        # Social media handles
        social_media_fields = ['linkedin', 'twitter', 'github', 'facebook', 'instagram', 'website']
        for field in social_media_fields:
            if field in data:
                update_fields[field] = data[field]
        
        if update_fields:
            db.users.update_one(
                {'_id': ObjectId(current_user_id)},
                {'$set': update_fields}
            )
            cache.delete(f"user_{current_user_id}")
        
        return jsonify({'message': 'Profile updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/profile/image', methods=['POST'])
@jwt_required()
def upload_profile_image():
    """Upload profile image and update user profile_image"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'Image file is required'}), 400

        image_file = request.files['image']
        if not image_file or image_file.filename == '':
            return jsonify({'error': 'Image file is required'}), 400

        upload_result = cloudinary.uploader.upload(
            image_file,
            folder='alumni_profiles',
            resource_type='image'
        )

        image_url = upload_result.get('secure_url')
        if not image_url:
            return jsonify({'error': 'Image upload failed'}), 500

        current_user_id = get_jwt_identity()
        db.users.update_one(
            {'_id': ObjectId(current_user_id)},
            {'$set': {'profile_image': image_url}}
        )
        cache.delete(f"user_{current_user_id}")

        return jsonify({'profile_image': image_url}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/profile/password', methods=['PUT'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        old_password = data.get('old_password')
        new_password = data.get('new_password')
        
        if not old_password or not new_password:
            return jsonify({'error': 'Both old and new passwords are required'}), 400
        
        if len(new_password) < 8:
            return jsonify({'error': 'New password must be at least 8 characters'}), 400
        
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        if not user or not check_password_hash(user['password'], old_password):
            return jsonify({'error': 'Invalid old password'}), 401
        
        db.users.update_one(
            {'_id': ObjectId(current_user_id)},
            {'$set': {'password': generate_password_hash(new_password)}}
        )
        
        return jsonify({'message': 'Password changed successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/auth/forgot-password', methods=['POST'])
@limiter.exempt
def forgot_password():
    """Send OTP for password reset"""
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Check if user exists
        user = db.users.find_one({'email': email})
        if not user:
            # For security, we return success but don't send email
            # This prevents email enumeration attacks
            app.logger.info(f"Password reset attempted for non-existent email: {email}")
            return jsonify({
                'message': 'If an account exists with this email, you will receive a password reset code',
                'email_sent': False  # Frontend can use this internally but shouldn't show to user
            }), 200
        
        # Generate OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Store OTP in temp_password_resets collection
        db.temp_password_resets.delete_many({'email': email})  # Remove any existing OTPs
        db.temp_password_resets.insert_one({
            'email': email,
            'otp': otp,
            'created_at': datetime.now(timezone.utc),
            'expires_at': datetime.now(timezone.utc) + timedelta(minutes=15)
        })
        
        # Send email with OTP
        email_sent = send_email_async(
            'Password Reset Request',
            f'<p>You requested to reset your password.</p>'
            f'<p>Your password reset code is: <strong style="font-size: 24px; color: #667eea;">{otp}</strong></p>'
            f'<p>This code will expire in 15 minutes.</p>'
            f'<p>If you did not request this, please ignore this email.</p>',
            email
        )
        
        return jsonify({
            'message': 'If an account exists with this email, you will receive a password reset code',
            'email_sent': True
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error in forgot_password: {str(e)}")
        return jsonify({'error': 'An error occurred. Please try again'}), 500


@app.route(f'/api/{API_VERSION}/auth/reset-password', methods=['POST'])
@limiter.exempt
def reset_password():
    """Verify OTP and reset password"""
    try:
        data = request.get_json()
        email = data.get('email')
        otp = data.get('otp')
        new_password = data.get('new_password')
        
        if not email or not otp or not new_password:
            return jsonify({'error': 'Email, OTP, and new password are required'}), 400
        
        if len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        # Find OTP record
        otp_record = db.temp_password_resets.find_one({'email': email, 'otp': otp})
        
        if not otp_record:
            return jsonify({'error': 'Invalid or expired OTP'}), 400
        
        # Check if OTP is expired
        created_at = otp_record['created_at']
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        
        time_elapsed = datetime.now(timezone.utc) - created_at
        if time_elapsed > timedelta(minutes=15):
            db.temp_password_resets.delete_one({'_id': otp_record['_id']})
            return jsonify({'error': 'OTP has expired. Please request a new one'}), 400
        
        # Update user password
        user = db.users.find_one({'email': email})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        db.users.update_one(
            {'_id': user['_id']},
            {'$set': {'password': generate_password_hash(new_password)}}
        )
        
        # Delete the OTP record
        db.temp_password_resets.delete_one({'_id': otp_record['_id']})
        
        # Send confirmation email
        send_email_async(
            'Password Reset Successful',
            f'<p>Your password has been successfully reset.</p>'
            f'<p>If you did not make this change, please contact support immediately.</p>',
            email
        )
        
        return jsonify({'message': 'Password reset successfully. You can now login with your new password'}), 200
        
    except Exception as e:
        app.logger.error(f"Error in reset_password: {str(e)}")
        return jsonify({'error': 'An error occurred. Please try again'}), 500


@app.route(f'/api/{API_VERSION}/users/<user_id>', methods=['GET'])
@jwt_required()
def get_user_profile(user_id):
    """Get specific user's public profile"""
    try:
        get_jwt_identity()
        
        try:
            obj_id = ObjectId(user_id)
        except Exception:
            return jsonify({'error': 'Invalid user id'}), 400
        
        user = db.users.find_one({'_id': obj_id})
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user = serialize_doc(user)
        user.pop('password', None)
        
        # Get user's approved articles
        articles = list(news_collection.find({
            'submitter_id': user_id,
            'status': 'approved'
        }).sort('submitted_at', -1).limit(10))
        
        user['articles'] = serialize_doc(articles)
        user['articles_count'] = news_collection.count_documents({
            'submitter_id': user_id,
            'status': 'approved'
        })
        
        # Get alumni profile (handle historical ObjectId/string user_id formats)
        alumni = alumni_collection.find_one({'user_id': {'$in': [user_id, obj_id]}})
        if alumni:
            serialized_alumni = serialize_doc(alumni)

            user['alumni_profile'] = serialized_alumni
        
        return jsonify({'profile': user}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    print(f"DEBUG: 404 on request: {request.path} {request.method}")
    app.logger.warning(f"404 on request: {request.path} {request.method}")
    return jsonify({'error': 'Endpoint not found', 'version': API_VERSION}), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({'error': 'Token has expired', 'version': API_VERSION}), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({'error': 'Invalid token'}), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({'error': 'Authorization token is missing'}), 401

# ============ ACHIEVEMENTS ENDPOINTS ============

@app.route(f'/api/{API_VERSION}/achievements', methods=['GET'])
def get_achievements():
    """Get all achievements - public endpoint with filtering"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 12))
        category = request.args.get('category', '')
        featured_only = request.args.get('featured', '').lower() == 'true'

        query = {}
        if category and category != 'all':
            query['category'] = category
        if featured_only:
            query['is_featured'] = True

        skip = (page - 1) * limit
        total = db.achievements.count_documents(query)

        # Featured first, then newest
        achievements = list(
            db.achievements.find(query)
            .sort([('is_featured', -1), ('created_at', -1)])
            .skip(skip)
            .limit(limit)
        )

        return jsonify({
            'achievements': serialize_doc(achievements),
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit
        }), 200
    except Exception as e:
        app.logger.error(f"Error fetching achievements: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/achievements/<achievement_id>', methods=['GET'])
def get_achievement(achievement_id):
    """Get single achievement - public endpoint"""
    try:
        achievement = db.achievements.find_one({'_id': ObjectId(achievement_id)})
        if not achievement:
            return jsonify({'error': 'Achievement not found'}), 404
        return jsonify({'achievement': serialize_doc(achievement)}), 200
    except Exception as e:
        app.logger.error(f"Error fetching achievement: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/achievements', methods=['POST'])
@admin_required
def create_achievement():
    """Create a new achievement - admin only, supports image upload"""
    try:
        import cloudinary.uploader as cl_uploader

        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'other').strip()
        student_name = request.form.get('student_name', '').strip() or None
        batch = request.form.get('batch', '').strip() or None
        date = request.form.get('date', '').strip()
        is_featured = request.form.get('is_featured', 'false').lower() == 'true'

        if not title:
            return jsonify({'error': 'Title is required'}), 400
        if not description:
            return jsonify({'error': 'Description is required'}), 400

        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                upload_result = cl_uploader.upload(
                    file,
                    folder='achievements',
                    transformation=[{'width': 1200, 'height': 800, 'crop': 'fill', 'quality': 'auto'}]
                )
                image_url = upload_result.get('secure_url')

        if not image_url:
            return jsonify({'error': 'Image is required'}), 400

        current_user_id = get_jwt_identity()

        achievement = {
            'title': title,
            'description': description,
            'image_url': image_url,
            'category': category,
            'student_name': student_name,
            'batch': batch,
            'date': date,
            'is_featured': is_featured,
            'reactions': {'like': [], 'love': [], 'celebrate': []},
            'reaction_count': 0,
            'comment_count': 0,
            'created_at': datetime.utcnow(),
            'created_by': ObjectId(current_user_id)
        }

        result = db.achievements.insert_one(achievement)
        achievement['_id'] = result.inserted_id

        actor = db.users.find_one({'_id': ObjectId(current_user_id)})
        actor_username = (actor or {}).get('username') if actor else None
        create_mention_notifications(
            f"{title}\n{description}",
            current_user_id,
            actor_username,
            'achievement',
            result.inserted_id,
            title
        )

        app.logger.info(f"Achievement created: {title} by admin {current_user_id}")
        return jsonify({
            'message': 'Achievement created successfully',
            'achievement': serialize_doc(achievement)
        }), 201
    except Exception as e:
        app.logger.error(f"Error creating achievement: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/achievements/<achievement_id>', methods=['PUT'])
@admin_required
def update_achievement(achievement_id):
    """Update an achievement - admin only"""
    try:
        import cloudinary.uploader as cl_uploader

        achievement = db.achievements.find_one({'_id': ObjectId(achievement_id)})
        if not achievement:
            return jsonify({'error': 'Achievement not found'}), 404

        updates = {}

        # Handle both JSON and form data
        if request.content_type and 'multipart' in request.content_type:
            data = request.form
        else:
            data = request.get_json() or {}

        if data.get('title'):
            updates['title'] = data['title'].strip()
        if data.get('description'):
            updates['description'] = data['description'].strip()
        if data.get('category'):
            updates['category'] = data['category'].strip()
        if 'student_name' in data:
            updates['student_name'] = data['student_name'].strip() or None
        if 'batch' in data:
            updates['batch'] = data['batch'].strip() or None
        if data.get('date'):
            updates['date'] = data['date'].strip()
        if 'is_featured' in data:
            val = data['is_featured']
            updates['is_featured'] = val if isinstance(val, bool) else str(val).lower() == 'true'

        # Handle new image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                upload_result = cl_uploader.upload(
                    file,
                    folder='achievements',
                    transformation=[{'width': 1200, 'height': 800, 'crop': 'fill', 'quality': 'auto'}]
                )
                updates['image_url'] = upload_result.get('secure_url')

        updates['updated_at'] = datetime.utcnow()

        db.achievements.update_one({'_id': ObjectId(achievement_id)}, {'$set': updates})
        updated = db.achievements.find_one({'_id': ObjectId(achievement_id)})

        current_user_id = get_jwt_identity()
        actor = db.users.find_one({'_id': ObjectId(current_user_id)})
        actor_username = (actor or {}).get('username') if actor else None
        mention_text = "\n".join([
            str(updates.get('title', achievement.get('title', ''))),
            str(updates.get('description', achievement.get('description', '')))
        ])
        create_mention_notifications(
            mention_text,
            current_user_id,
            actor_username,
            'achievement',
            ObjectId(achievement_id),
            str(updates.get('title', achievement.get('title', '')))
        )

        return jsonify({
            'message': 'Achievement updated successfully',
            'achievement': serialize_doc(updated)
        }), 200
    except Exception as e:
        app.logger.error(f"Error updating achievement: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/achievements/<achievement_id>', methods=['DELETE'])
@admin_required
def delete_achievement(achievement_id):
    """Delete an achievement - admin only"""
    try:
        achievement = db.achievements.find_one({'_id': ObjectId(achievement_id)})
        if not achievement:
            return jsonify({'error': 'Achievement not found'}), 404

        db.achievements.delete_one({'_id': ObjectId(achievement_id)})
        app.logger.info(f"Achievement deleted: {achievement_id}")
        return jsonify({'message': 'Achievement deleted successfully'}), 200
    except Exception as e:
        app.logger.error(f"Error deleting achievement: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/achievements/<achievement_id>/reactions', methods=['POST'])
@jwt_required()
def toggle_achievement_reaction(achievement_id):
    """Toggle a reaction on an achievement"""
    try:
        try:
            obj_id = ObjectId(achievement_id)
        except Exception:
            return jsonify({'error': 'Invalid achievement id'}), 400

        data = request.get_json() or {}
        reaction_type = data.get('type')

        if reaction_type not in ['like', 'love', 'celebrate']:
            return jsonify({'error': 'Invalid reaction type. Must be: like, love, or celebrate'}), 400

        achievement = db.achievements.find_one({'_id': obj_id})
        if not achievement:
            return jsonify({'error': 'Achievement not found'}), 404

        current_user_id = get_jwt_identity()

        if 'reactions' not in achievement:
            achievement['reactions'] = {'like': [], 'love': [], 'celebrate': []}

        user_reactions = achievement.get('reactions', {})
        reaction_list = user_reactions.get(reaction_type, [])

        if current_user_id in reaction_list:
            db.achievements.update_one(
                {'_id': obj_id},
                {
                    '$pull': {f'reactions.{reaction_type}': current_user_id},
                    '$inc': {'reaction_count': -1}
                }
            )
            action = 'removed'
        else:
            for rtype in ['like', 'love', 'celebrate']:
                if rtype != reaction_type and current_user_id in user_reactions.get(rtype, []):
                    db.achievements.update_one(
                        {'_id': obj_id},
                        {'$pull': {f'reactions.{rtype}': current_user_id}}
                    )

            db.achievements.update_one(
                {'_id': obj_id},
                {
                    '$addToSet': {f'reactions.{reaction_type}': current_user_id},
                    '$inc': {'reaction_count': 1}
                }
            )
            action = 'added'

        updated = db.achievements.find_one({'_id': obj_id}, {'reactions': 1, 'reaction_count': 1})
        reactions = updated.get('reactions', {})

        return jsonify({
            'message': f'Reaction {action}',
            'action': action,
            'reactions': {
                'like': len(reactions.get('like', [])),
                'love': len(reactions.get('love', [])),
                'celebrate': len(reactions.get('celebrate', []))
            },
            'total_reactions': updated.get('reaction_count', 0),
            'user_reaction': reaction_type if action == 'added' else None
        }), 200
    except Exception as e:
        app.logger.error(f"Toggle achievement reaction error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/achievements/<achievement_id>/reactions', methods=['GET'])
def get_achievement_reactions(achievement_id):
    """Get reactions for an achievement"""
    try:
        try:
            obj_id = ObjectId(achievement_id)
        except Exception:
            return jsonify({'error': 'Invalid achievement id'}), 400

        achievement = db.achievements.find_one({'_id': obj_id}, {'reactions': 1, 'reaction_count': 1})
        if not achievement:
            return jsonify({'error': 'Achievement not found'}), 404

        reactions = achievement.get('reactions', {})
        current_user_id = get_jwt_identity() if request.headers.get('Authorization') else None
        user_reaction = None

        if current_user_id:
            for rtype in ['like', 'love', 'celebrate']:
                if current_user_id in reactions.get(rtype, []):
                    user_reaction = rtype
                    break

        return jsonify({
            'reactions': {
                'like': len(reactions.get('like', [])),
                'love': len(reactions.get('love', [])),
                'celebrate': len(reactions.get('celebrate', []))
            },
            'total_reactions': achievement.get('reaction_count', 0),
            'user_reaction': user_reaction
        }), 200
    except Exception as e:
        app.logger.error(f"Get achievement reactions error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/achievements/<achievement_id>/comments', methods=['GET'])
def get_achievement_comments(achievement_id):
    """Get comments for an achievement"""
    try:
        try:
            obj_id = ObjectId(achievement_id)
        except Exception:
            return jsonify({'error': 'Invalid achievement id'}), 400

        achievement = db.achievements.find_one({'_id': obj_id})
        if not achievement:
            return jsonify({'error': 'Achievement not found'}), 404

        comments = list(db.achievement_comments.find({'achievement_id': obj_id}).sort('created_at', DESCENDING))

        return jsonify({
            'comments': serialize_doc(comments),
            'total': len(comments)
        }), 200
    except Exception as e:
        app.logger.error(f"Get achievement comments error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/achievements/<achievement_id>/comments', methods=['POST'])
@jwt_required()
def create_achievement_comment(achievement_id):
    """Create comment on an achievement"""
    try:
        try:
            obj_id = ObjectId(achievement_id)
        except Exception:
            return jsonify({'error': 'Invalid achievement id'}), 400

        achievement = db.achievements.find_one({'_id': obj_id})
        if not achievement:
            return jsonify({'error': 'Achievement not found'}), 404

        data = request.get_json() or {}
        content = data.get('content', '').strip()
        if not content:
            return jsonify({'error': 'Comment content is required'}), 400
        if len(content) > 1000:
            return jsonify({'error': 'Comment too long (max 1000 characters)'}), 400

        current_user_id = get_jwt_identity()
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404

        comment = {
            'achievement_id': obj_id,
            'user_id': ObjectId(current_user_id),
            'author_name': user.get('full_name') or user.get('username') or 'User',
            'author_image': user.get('profile_image'),
            'content': content,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'is_edited': False
        }

        result = db.achievement_comments.insert_one(comment)
        comment['_id'] = result.inserted_id

        db.achievements.update_one({'_id': obj_id}, {'$inc': {'comment_count': 1}})

        create_mention_notifications(
            content,
            current_user_id,
            user.get('username'),
            'achievement comment',
            obj_id,
            content
        )

        return jsonify({'message': 'Comment created successfully', 'comment': serialize_doc(comment)}), 201
    except Exception as e:
        app.logger.error(f"Create achievement comment error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    """Get current user's notifications"""
    try:
        current_user_id = get_jwt_identity()
        page = max(int(request.args.get('page', 1)), 1)
        limit = min(max(int(request.args.get('limit', 20)), 1), 100)

        query = {'user_id': ObjectId(current_user_id)}
        total = db.notifications.count_documents(query)
        unread_count = db.notifications.count_documents({'user_id': ObjectId(current_user_id), 'is_read': False})
        notifications = list(
            db.notifications.find(query)
            .sort('created_at', DESCENDING)
            .skip((page - 1) * limit)
            .limit(limit)
        )

        return jsonify({
            'notifications': serialize_doc(notifications),
            'unread_count': unread_count,
            'pagination': {
                'page': page,
                'per_page': limit,
                'total': total,
                'pages': (total + limit - 1) // limit
            }
        }), 200
    except Exception as e:
        app.logger.error(f"Get notifications error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/notifications/<notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_notification_read(notification_id):
    """Mark one notification as read"""
    try:
        current_user_id = get_jwt_identity()
        db.notifications.update_one(
            {'_id': ObjectId(notification_id), 'user_id': ObjectId(current_user_id)},
            {'$set': {'is_read': True, 'read_at': datetime.now(timezone.utc)}}
        )
        return jsonify({'message': 'Notification marked as read'}), 200
    except Exception as e:
        app.logger.error(f"Mark notification read error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/notifications/read-all', methods=['PUT'])
@jwt_required()
def mark_all_notifications_read():
    """Mark all notifications as read"""
    try:
        current_user_id = get_jwt_identity()
        db.notifications.update_many(
            {'user_id': ObjectId(current_user_id), 'is_read': False},
            {'$set': {'is_read': True, 'read_at': datetime.now(timezone.utc)}}
        )
        return jsonify({'message': 'All notifications marked as read'}), 200
    except Exception as e:
        app.logger.error(f"Mark all notifications read error: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ============ ALUMNI GALLERY ENDPOINTS ============

@app.route(f'/api/{API_VERSION}/gallery', methods=['GET'])
def get_gallery_items():
    """Get alumni gallery images with pagination and optional year filter"""
    try:
        page = max(int(request.args.get('page', 1)), 1)
        limit = min(max(int(request.args.get('limit', 12)), 1), 50)
        year = request.args.get('year')

        query = {}
        if year:
            try:
                query['year'] = int(year)
            except Exception:
                return jsonify({'error': 'Invalid year filter'}), 400

        skip = (page - 1) * limit
        total = db.alumni_gallery.count_documents(query)

        items = list(
            db.alumni_gallery.find(query)
            .sort([('year', DESCENDING), ('created_at', DESCENDING)])
            .skip(skip)
            .limit(limit)
        )

        available_years = db.alumni_gallery.distinct('year')
        available_years = sorted([y for y in available_years if isinstance(y, int)], reverse=True)

        return jsonify({
            'items': serialize_doc(items),
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit,
            'years': available_years
        }), 200
    except Exception as e:
        app.logger.error(f"Error fetching gallery items: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/gallery', methods=['POST'])
@admin_required
def create_gallery_item():
    """Create gallery item (admin only)"""
    try:
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        event_name = request.form.get('event_name', '').strip()
        year_raw = request.form.get('year', '').strip()

        if not title:
            return jsonify({'error': 'Title is required'}), 400
        if not year_raw:
            return jsonify({'error': 'Year is required'}), 400

        try:
            year = int(year_raw)
        except Exception:
            return jsonify({'error': 'Year must be a valid number'}), 400

        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                upload_result = cloudinary.uploader.upload(
                    file,
                    folder='alumni_gallery',
                    transformation=[{'width': 1920, 'height': 1080, 'crop': 'limit', 'quality': 'auto:best'}]
                )
                image_url = upload_result.get('secure_url')

        if not image_url:
            return jsonify({'error': 'Image is required'}), 400

        current_user_id = get_jwt_identity()
        item = {
            'title': title,
            'description': description,
            'event_name': event_name if event_name else title,
            'year': year,
            'image_url': image_url,
            'created_by': ObjectId(current_user_id),
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }

        result = db.alumni_gallery.insert_one(item)
        item['_id'] = result.inserted_id

        return jsonify({'message': 'Gallery item created successfully', 'item': serialize_doc(item)}), 201
    except Exception as e:
        app.logger.error(f"Error creating gallery item: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/gallery/<item_id>', methods=['PUT'])
@admin_required
def update_gallery_item(item_id):
    """Update gallery item (admin only)"""
    try:
        existing = db.alumni_gallery.find_one({'_id': ObjectId(item_id)})
        if not existing:
            return jsonify({'error': 'Gallery item not found'}), 404

        updates = {}
        if request.content_type and 'multipart' in request.content_type:
            data = request.form
        else:
            data = request.get_json() or {}

        if 'title' in data:
            updates['title'] = str(data.get('title', '')).strip()
        if 'description' in data:
            updates['description'] = str(data.get('description', '')).strip()
        if 'event_name' in data:
            updates['event_name'] = str(data.get('event_name', '')).strip()
        if 'year' in data and str(data.get('year')).strip():
            try:
                updates['year'] = int(str(data.get('year')).strip())
            except Exception:
                return jsonify({'error': 'Year must be a valid number'}), 400

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                upload_result = cloudinary.uploader.upload(
                    file,
                    folder='alumni_gallery',
                    transformation=[{'width': 1920, 'height': 1080, 'crop': 'limit', 'quality': 'auto:best'}]
                )
                updates['image_url'] = upload_result.get('secure_url')

        if not updates:
            return jsonify({'error': 'No updates provided'}), 400

        updates['updated_at'] = datetime.now(timezone.utc)
        db.alumni_gallery.update_one({'_id': ObjectId(item_id)}, {'$set': updates})
        updated = db.alumni_gallery.find_one({'_id': ObjectId(item_id)})

        return jsonify({'message': 'Gallery item updated successfully', 'item': serialize_doc(updated)}), 200
    except Exception as e:
        app.logger.error(f"Error updating gallery item: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/gallery/<item_id>', methods=['DELETE'])
@admin_required
def delete_gallery_item(item_id):
    """Delete gallery item (admin only)"""
    try:
        existing = db.alumni_gallery.find_one({'_id': ObjectId(item_id)})
        if not existing:
            return jsonify({'error': 'Gallery item not found'}), 404

        db.alumni_gallery.delete_one({'_id': ObjectId(item_id)})
        return jsonify({'message': 'Gallery item deleted successfully'}), 200
    except Exception as e:
        app.logger.error(f"Error deleting gallery item: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ============ STUDENT STARTUPS ENDPOINTS ============

@app.route(f'/api/{API_VERSION}/startups', methods=['GET'])
def get_startups():
    """Get startup entries with pagination"""
    try:
        page = max(int(request.args.get('page', 1)), 1)
        limit = min(max(int(request.args.get('limit', 10)), 1), 50)
        year = request.args.get('year')

        query = {}
        if year:
            try:
                query['year'] = int(year)
            except Exception:
                return jsonify({'error': 'Invalid year filter'}), 400

        skip = (page - 1) * limit
        total = db.student_startups.count_documents(query)

        startups = list(
            db.student_startups.find(query)
            .sort([('is_featured', DESCENDING), ('year', DESCENDING), ('created_at', DESCENDING)])
            .skip(skip)
            .limit(limit)
        )

        available_years = db.student_startups.distinct('year')
        available_years = sorted([y for y in available_years if isinstance(y, int)], reverse=True)

        return jsonify({
            'startups': serialize_doc(startups),
            'total': total,
            'page': page,
            'pages': (total + limit - 1) // limit,
            'years': available_years
        }), 200
    except Exception as e:
        app.logger.error(f"Error fetching startups: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/startups', methods=['POST'])
@admin_required
def create_startup():
    """Create startup entry (admin only)"""
    try:
        data = request.get_json() or {}

        name = str(data.get('name', '')).strip()
        description = str(data.get('description', '')).strip()
        website_url = str(data.get('website_url', '')).strip()
        founder_name = str(data.get('founder_name', '')).strip()
        year_raw = data.get('year')
        is_featured = bool(data.get('is_featured', False))

        if not name:
            return jsonify({'error': 'Startup name is required'}), 400
        if not description:
            return jsonify({'error': 'Description is required'}), 400

        year = None
        if year_raw not in (None, ''):
            try:
                year = int(year_raw)
            except Exception:
                return jsonify({'error': 'Year must be a valid number'}), 400

        current_user_id = get_jwt_identity()
        startup = {
            'name': name,
            'description': description,
            'website_url': website_url,
            'founder_name': founder_name,
            'year': year,
            'is_featured': is_featured,
            'created_by': ObjectId(current_user_id),
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }

        result = db.student_startups.insert_one(startup)
        startup['_id'] = result.inserted_id

        return jsonify({'message': 'Startup created successfully', 'startup': serialize_doc(startup)}), 201
    except Exception as e:
        app.logger.error(f"Error creating startup: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/startups/<startup_id>', methods=['PUT'])
@admin_required
def update_startup(startup_id):
    """Update startup entry (admin only)"""
    try:
        existing = db.student_startups.find_one({'_id': ObjectId(startup_id)})
        if not existing:
            return jsonify({'error': 'Startup not found'}), 404

        data = request.get_json() or {}
        updates = {}

        if 'name' in data:
            updates['name'] = str(data.get('name', '')).strip()
        if 'description' in data:
            updates['description'] = str(data.get('description', '')).strip()
        if 'website_url' in data:
            updates['website_url'] = str(data.get('website_url', '')).strip()
        if 'founder_name' in data:
            updates['founder_name'] = str(data.get('founder_name', '')).strip()
        if 'year' in data:
            year_value = data.get('year')
            if year_value in (None, ''):
                updates['year'] = None
            else:
                try:
                    updates['year'] = int(year_value)
                except Exception:
                    return jsonify({'error': 'Year must be a valid number'}), 400
        if 'is_featured' in data:
            updates['is_featured'] = bool(data.get('is_featured'))

        if not updates:
            return jsonify({'error': 'No updates provided'}), 400

        updates['updated_at'] = datetime.now(timezone.utc)

        db.student_startups.update_one({'_id': ObjectId(startup_id)}, {'$set': updates})
        updated = db.student_startups.find_one({'_id': ObjectId(startup_id)})

        return jsonify({'message': 'Startup updated successfully', 'startup': serialize_doc(updated)}), 200
    except Exception as e:
        app.logger.error(f"Error updating startup: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/startups/<startup_id>', methods=['DELETE'])
@admin_required
def delete_startup(startup_id):
    """Delete startup entry (admin only)"""
    try:
        existing = db.student_startups.find_one({'_id': ObjectId(startup_id)})
        if not existing:
            return jsonify({'error': 'Startup not found'}), 404

        db.student_startups.delete_one({'_id': ObjectId(startup_id)})
        return jsonify({'message': 'Startup deleted successfully'}), 200
    except Exception as e:
        app.logger.error(f"Error deleting startup: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ============ REGISTER BLUEPRINTS ============
# Import and register comments blueprint
try:
    from comments_endpoints import comments_bp, init_comments_blueprint
    init_comments_blueprint(db, app.logger)
    app.register_blueprint(comments_bp)
    app.logger.info("Comments blueprint registered successfully")
except Exception as e:
    app.logger.error(f"Error registering comments blueprint: {str(e)}")


# ============ ANALYTICS ENDPOINTS ============

@app.route(f'/api/{API_VERSION}/admin/analytics/user-growth', methods=['GET'])
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
        app.logger.error(f"Error getting user growth: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/analytics/category-distribution', methods=['GET'])
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
        app.logger.error(f"Error getting category distribution: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/analytics/engagement-metrics', methods=['GET'])
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
        app.logger.error(f"Error getting engagement metrics: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/analytics/alumni-by-year', methods=['GET'])
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
        app.logger.error(f"Error getting alumni by year: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/analytics/department-distribution', methods=['GET'])
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
        app.logger.error(f"Error getting department distribution: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/analytics/recent-activity', methods=['GET'])
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
        app.logger.error(f"Error getting recent activity: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/analytics/stats-summary', methods=['GET'])
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
        app.logger.error(f"Error getting stats summary: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/analytics/top-articles', methods=['GET'])
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
        
        return jsonify({
            'top_by_views': serialize_doc(top_by_views),
            'top_by_reactions': serialize_doc(top_by_reactions)
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error getting top articles: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/analytics/user-activity-heatmap', methods=['GET'])
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
        app.logger.error(f"Error getting user activity heatmap: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route(f'/api/{API_VERSION}/admin/analytics/content-performance', methods=['GET'])
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
        app.logger.error(f"Error getting content performance: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # List registered routes for debugging
    print("\n=== Registered Routes ===")
    for rule in app.url_map.iter_rules():
        if '/api/' in rule.rule:
            print(f"{rule.rule} {rule.methods}")
    print("=== End Routes ===\n")
    app.run(debug=False, host='0.0.0.0', port=5000)



