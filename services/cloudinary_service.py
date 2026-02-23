"""
Cloudinary service for file uploads
"""
import cloudinary
import cloudinary.uploader
import cloudinary.api
import logging

logger = logging.getLogger(__name__)


class CloudinaryService:
    """Cloudinary file upload service"""
    
    def __init__(self, app=None):
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app config"""
        cloudinary.config(
            cloud_name=app.config.get('CLOUDINARY_CLOUD_NAME'),
            api_key=app.config.get('CLOUDINARY_API_KEY'),
            api_secret=app.config.get('CLOUDINARY_API_SECRET')
        )
    
    def upload_image(self, file, folder='uploads'):
        """Upload image to Cloudinary"""
        try:
            result = cloudinary.uploader.upload(
                file,
                folder=folder,
                resource_type='image'
            )
            return result.get('secure_url')
        except Exception as e:
            logger.error(f"Cloudinary upload error: {str(e)}")
            raise
    
    def upload_file(self, file, folder='uploads', resource_type='auto'):
        """Upload any file to Cloudinary"""
        try:
            result = cloudinary.uploader.upload(
                file,
                folder=folder,
                resource_type=resource_type
            )
            return {
                'url': result.get('secure_url'),
                'public_id': result.get('public_id')
            }
        except Exception as e:
            logger.error(f"Cloudinary upload error: {str(e)}")
            raise


# Global instance
cloudinary_service = CloudinaryService()
