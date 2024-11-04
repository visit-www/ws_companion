import os
from datetime import timedelta
import uuid
import dotenv

# Load environment variables from.env file if present
dotenv.load_dotenv()


basedir=os.path.abspath(os.path.dirname(__file__))
# Set user_dir to the path of the user_data directory one level up from the current file
userdir = os.path.join(basedir, 'user_data')
creativesfolder = os.path.join(basedir, 'creatives_folder')
ANONYMOUS_USER_ID = uuid.UUID('123e4567-e89b-12d3-a456-426614174000')
ANONYMOUS_EMAIL = os.getenv('ANONYMOUS_EMAIL', "anonymous_user@example.com")
ANONYMOUS_PASSWORD = os.getenv('ANONYMOUS_PASSWORD', "defaultanonymouspassword")  # Fixed typo
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', "admin@example.com")
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', "defaultadminpassword")

class Config:
    SECRET_KEY=os.getenv('SECRET_KEY') or '7ebfffbf75e406f1b63739a0c5e487496be74113d2fd3a672fc45b4a120f571b'
    WTF_CSRF_ENABLED = True
    SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL') or 'postgresql://admin:811976@localhost:5432/wscdb?sslmode=require'
    # Convert Heroku's default postgres:// to postgresql:// if needed
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

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