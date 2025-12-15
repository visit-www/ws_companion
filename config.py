import os
from datetime import timedelta
import uuid
import dotenv

# Load environment variables from .env file if present
dotenv.load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
userdir = os.path.join(basedir, 'user_data')
creativesfolder = os.path.join(basedir, 'creatives_folder')

ANONYMOUS_USER_ID = uuid.UUID('123e4567-e89b-12d3-a456-426614174000')
ANONYMOUS_EMAIL = os.getenv('ANONYMOUS_EMAIL', "anonymous_user@example.com")
ANONYMOUS_PASSWORD = os.getenv('ANONYMOUS_PASSWORD', "defaultanonymouspassword")
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', "wscompanionapp@gmail.com")
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', "defaultadminpassword")

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or '7ebfffbf75e406f1b63739a0c5e487496be74113d2fd3a672fc45b4a120f571b'
    WTF_CSRF_ENABLED = True

    # Detect env
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')

    # Load DB URL
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')

    # Default fallback for local
    if not SQLALCHEMY_DATABASE_URI or FLASK_ENV == 'development':
        SQLALCHEMY_DATABASE_URI = 'postgresql://admin:811976@localhost:5432/wscdb?sslmode=disable'

    # Convert Heroku's default postgres:// to postgresql:// if needed
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'files')
    CERTIFICATE_UPLOAD_FOLDER = os.path.join(basedir, 'uploads', 'certificates')
    
    # Session Settings
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'ws_companion_app_session_cookie'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_IDLE_TIMEOUT = timedelta(minutes=30)
    SESSION_WARNING_TIME = timedelta(minutes=5)
    # Mail settings
    MAIL_SERVER = 'smtp-relay.brevo.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('BREVO_SMTP_USERNAME')
    MAIL_PASSWORD = os.getenv('BREVO_SMTP_KEY')  # no hard-coded secret
    MAIL_DEFAULT_SENDER = ('My Workstation Companion App', 'wscompanionapp@gmail.com')
    SECURITY_PASSWORD_SALT = '25df2a0675d39147e5e8f1bf75550f2a'
    MAIL_MAX_EMAILS = None
    MAIL_ASCII_ATTACHMENTS = False

    # AI helper cards (feature-flag + provider config)
    AI_HELPERS_ENABLED = os.getenv('AI_HELPERS_ENABLED', 'false').lower() == 'true'
    AI_PROVIDER = os.getenv('AI_PROVIDER')
    AI_MODEL = os.getenv('QUBRID_MODEL')  # Using Qubrid model as default
    AI_MAX_TOKENS = int(os.getenv('AI_MAX_TOKENS', '1500'))
    AI_REQUEST_TIMEOUT = int(os.getenv('AI_REQUEST_TIMEOUT'))  # seconds
    AI_FREE_DAILY_LIMIT = int(os.getenv('AI_FREE_DAILY_LIMIT'))
    AI_PAID_DAILY_LIMIT = int(os.getenv('AI_PAID_DAILY_LIMIT'))
    _max_calls_raw = os.getenv('AI_MAX_DAILY_CALLS_PER_USER')
    AI_MAX_DAILY_CALLS_PER_USER = int(_max_calls_raw) if _max_calls_raw is not None else 50  # fallback cap
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    QUBRID_API_KEY = os.getenv('QUBRID_API_KEY')
    QUBRID_MODEL = os.getenv('QUBRID_MODEL')
