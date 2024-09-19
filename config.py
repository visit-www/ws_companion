import os
from datetime import timedelta
basedir=os.path.abspath(os.path.dirname(__file__))
# Set user_dir to the path of the user_data directory one level up from the current file
userdir = os.path.join(basedir, 'user_data')
class Config:
    SECRET_KEY=os.getenv('SECRET_KEY') or '7ebfffbf75e406f1b63739a0c5e487496be74113d2fd3a672fc45b4a120f571b'
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL') or 'postgresql://admin:811976@localhost:5432/wscdb'
    SQLALCHEMY_TRACK_MODIFICATIONS=False
    UPLOAD_FOLDER=os.path.join(basedir, 'files')

    # Use secure cookies
    SESSION_COOKIE_SECURE = False  # Ensures cookies are only sent over HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevents JavaScript access to cookies
    SESSION_COOKIE_SAMESITE = 'Lax'  # Restrict cross-site cookie access
    SESSION_COOKIE_NAME = 'ws_companion_app_session_cookie'  # Set a specific name for your session cookie
    PERMANENT_SESSION_LIFETIME = timedelta (days=1)  # Set session lifetime to 30 days
    SESSION_IDLE_TIMEOUT = timedelta(minutes=30)  # Set total idle timeout
    SESSION_WARNING_TIME = timedelta(minutes=5)   # Warn the user 5 minutes before timeout
    
    # Mail realted configurations...
    MAIL_SERVER = 'smtp-relay.brevo.com'  # Replace with your SMTP server
    MAIL_PORT = 587  # Common port for TLS
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('BREVO_SMTP_USERNAME')  # Your email address
    MAIL_PASSWORD = 'zkZg1Dphfb7BX25G'  # Your email password
    MAIL_DEFAULT_SENDER = ('My Workstation Companion App', 'support@wscompanion.com')  # Default sender info
    SECURITY_PASSWORD_SALT = '25df2a0675d39147e5e8f1bf75550f2a'  # Add this if it's not already defined
    MAIL_MAX_EMAILS = None
    MAIL_ASCII_ATTACHMENTS = False