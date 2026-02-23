"""
Flask extensions initialization
Centralizes all Flask extension instances
"""
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_compress import Compress

# Initialize extensions (will be configured in create_app)
cors = CORS()
jwt = JWTManager()
cache = Cache()
compress = Compress()
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://"
)
