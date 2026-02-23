"""
Configuration module for TSSM Alumni Backend
Centralizes all configuration settings
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.urandom(24).hex())
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Cache
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 600
    CACHE_THRESHOLD = 1000
    
    # Compression
    COMPRESS_MIMETYPES = [
        'text/html', 'text/css', 'text/xml', 'application/json',
        'application/javascript', 'text/javascript'
    ]
    COMPRESS_LEVEL = 6
    COMPRESS_MIN_SIZE = 500
    
    # CORS
    CORS_ORIGINS = [
        "https://bscoeralumni.vercel.app",
    ]
    
    # Rate Limiting
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_DEFAULT = ["10000 per day", "1000 per hour"]
    
    # MongoDB
    MONGODB_URI = os.getenv('MONGODB_URI')
    MONGODB_SETTINGS = {
        'serverSelectionTimeoutMS': 15000,
        'retryWrites': True,
        'connectTimeoutMS': 15000,
        'maxPoolSize': 50,
        'minPoolSize': 10,
        'maxIdleTimeMS': 45000,
        'waitQueueTimeoutMS': 10000,
        'compressors': 'snappy,zlib',
        'zlibCompressionLevel': 6
    }
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')
    
    # Email - Brevo
    BREVO_SMTP_SERVER = os.getenv('BREVO_SMTP_SERVER', 'smtp-relay.brevo.com')
    BREVO_SMTP_PORT = int(os.getenv('BREVO_SMTP_PORT', '587'))
    BREVO_EMAIL = os.getenv('BREVO_EMAIL')
    BREVO_API_KEY = os.getenv('BREVO_API_KEY')
    BREVO_API_URL = os.getenv('BREVO_API_URL', 'https://api.brevo.com/v3/smtp/email')
    
    # Email - Gmail Fallback
    GMAIL_EMAIL = os.getenv('GMAIL_EMAIL')
    GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
    
    # Admin
    ADMIN_KEY = os.getenv('ADMIN_KEY')
    
    # API
    API_VERSION = "v1"
    
    # Logging
    LOG_DIR = 'logs'
    LOG_FILE = 'logs/alumni_api.log'
    LOG_MAX_BYTES = 10240000
    LOG_BACKUP_COUNT = 10
