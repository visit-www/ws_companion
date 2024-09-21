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
    
    # Default app initialization
import json
from datetime import datetime, timezone
from .models import db,Content, User, UserData, UserContentState, AdminReportTemplate
from config import basedir
import os


def add_default_admin(admin_data):
    """Add admin user if not already present."""
    admin_user = db.session.query(User).filter_by(email=admin_data['email']).first()
    if not admin_user:
        new_admin = User(
            username=admin_data['username'],
            email=admin_data['email'],
            is_paid=admin_data['is_paid'],
            is_admin=admin_data['is_admin']
        )
        new_admin.set_password(admin_data['password'])
        db.session.add(new_admin)
        db.session.commit()

        print(f"Admin user created: {new_admin.username}, {new_admin.email}")

        # Initialize UserData for the admin
        user_data = UserData(
            user_id=new_admin.id,
            interaction_type='registered',
            time_spent=0,
            last_interaction=datetime.now(timezone.utc),
            last_login=datetime.now(timezone.utc)
        )
        db.session.add(user_data)

        # Initialize UserContentState for the admin
        user_content_state = UserContentState(
            user_id=new_admin.id,
            modified_filepath=None,
            annotations=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.session.add(user_content_state)
        # Initialize AdminReportTemplate with
        admin_report_template = AdminReportTemplate(
            template_name=None,
                body_part= None,
                modality=None,
                file=None,
                filepath=None,
                tags=None,
                category=None,
                module=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
                )
        db.session.add(admin_report_template)
        db.session.commit()
        print(f"Admin data initialized.")
    else:
        print(f"Admin already exists: {admin_user.username}")
# Crreate Anonymous user to relate to orphaned data after users or content is delated (referecnes, userfeedback)
from config import ANONYMOUS_USER_ID
def add_anonymous_user():
    anonymous_user = db.session.query(User).filter_by(username='anonymous').first()
    try:
        if not anonymous_user:
            # Create anonymous user
            anonymous_user = User(
                id=ANONYMOUS_USER_ID,
                username='anonymous',
                email='lotusheart2016s@gmail.com',
                is_paid=False,
                is_admin=False,
                status='active',
            )
            anonymous_user.set_password('EraRam@2024')
            db.session.add(anonymous_user)
            db.session.commit()
            print(f"Anonymous user created: {anonymous_user}, {anonymous_user.email}")
        else:
            print(f"Anonymous user already exists: {anonymous_user.username}")
    except Exception as e:
        print(f"Error adding anonymous user: {e}")


def add_default_contents(contents_data):
    """Add default contents if not already present."""
    for content_data in contents_data:
        existing_content = db.session.query(Content).filter_by(title=content_data['title']).first()
        if not existing_content:
            new_content = Content(
                title=content_data['title'],
                category=content_data['category'],
                module=content_data['module'],
                status=content_data['status'],
                embed_code=content_data['embed_code'],
                description=content_data['description'],
                created_by=content_data['created_by'],
                language=content_data['language'],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.session.add(new_content)
            print(f"Content added: {new_content.title}")
        else:
            print(f"Content already exists: {existing_content.title}")
    

    db.session.commit()
    print("Default contents loaded successfully.")

def load_default_data():
    """Load default admin and content data from JSON."""
    json_filepath= os.path.join(basedir,'app','default_data.json')
    try:
        with open(json_filepath) as f:
            default_data = json.load(f)
            print("json file loaded")
            return default_data
    except FileNotFoundError:
        print("default_data.json not found")
        return None

