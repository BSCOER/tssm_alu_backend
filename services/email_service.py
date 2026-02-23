"""
Email service for sending emails via Brevo or Gmail
"""
import smtplib
import requests
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Email service handler"""
    
    def __init__(self, app=None):
        self.app = app
        self.brevo_email = None
        self.brevo_api_key = None
        self.brevo_api_url = None
        self.gmail_email = None
        self.gmail_password = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app config"""
        self.app = app
        self.brevo_email = app.config.get('BREVO_EMAIL')
        self.brevo_api_key = app.config.get('BREVO_API_KEY')
        self.brevo_api_url = app.config.get('BREVO_API_URL')
        self.gmail_email = app.config.get('GMAIL_EMAIL')
        self.gmail_password = app.config.get('GMAIL_APP_PASSWORD')
    
    def can_send_email(self):
        """Check if email service is configured"""
        if self.brevo_email and self.brevo_api_key:
            return True
        if self.gmail_email and self.gmail_password:
            return True
        logger.error("No email service configured")
        return False
    
    def send_email_async(self, subject, message, recipient_email):
        """Send email in a background thread to avoid blocking requests"""
        if not self.can_send_email():
            return False

        def _task():
            try:
                self.send_email(subject, message, recipient_email)
            except Exception as e:
                logger.error(f"Async email error: {str(e)}")

        thread = threading.Thread(target=_task, daemon=True)
        thread.start()
        return True
    
    def send_email(self, subject, message, recipient_email):
        """Send email via Brevo HTTP API (primary) or Gmail (fallback) SMTP"""
        from utils.helpers import retry_operation
        
        @retry_operation
        def _send():
            # Try Brevo HTTP API first
            if self.brevo_email and self.brevo_api_key:
                logger.info("Using Brevo for email delivery")
                payload = {
                    "sender": {"name": "TSSM Alumni Portal", "email": self.brevo_email},
                    "to": [{"email": recipient_email}],
                    "subject": subject,
                    "htmlContent": message,
                }
                headers = {
                    "accept": "application/json",
                    "api-key": self.brevo_api_key,
                    "content-type": "application/json",
                }
                response = requests.post(self.brevo_api_url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                return True
            
            # Fallback to Gmail
            elif self.gmail_email and self.gmail_password:
                logger.info("Using Gmail for email delivery")
                return self._send_via_gmail(subject, message, recipient_email)
            else:
                logger.error("No email service configured")
                return False
        
        try:
            return _send()
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def _send_via_gmail(self, subject, message, recipient_email):
        """Send email via Gmail SMTP"""
        from database import db
        
        settings = db.settings.find_one() or {} if db else {}
        smtp_server = settings.get('smtp_server', 'smtp.gmail.com')
        smtp_port = int(settings.get('smtp_port', '587'))
        sender_email = self.gmail_email
        sender_password = self.gmail_password
        
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
                            <p style="color: #666; margin: 0; font-size: 12px;">© {datetime.now(timezone.utc).year} TSSM Alumni Portal. All rights reserved.</p>
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


# Global instance
email_service = EmailService()
