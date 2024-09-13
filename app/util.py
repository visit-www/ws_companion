# * Imports
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app

def generate_password_reset_token(data, expiration=600):
    """Generate a secure token for given data."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(data, salt=current_app.config['SECURITY_PASSWORD_SALT'])

def verify_password_reset_token(token, expiration=600):
    """Verify a password reset token and return the associated data if valid."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, salt=current_app.config['SECURITY_PASSWORD_SALT'], max_age=expiration)
        return data
    except (BadSignature, SignatureExpired):
        return None