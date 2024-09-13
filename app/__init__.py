from flask import Flask, request, redirect, url_for, flash,session
from flask_login import current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager
import sqlalchemy.orm as so
from typing import Type
import logging
import os
from datetime import datetime,timedelta,timezone
from flask_mail import Mail

# Initialize the registry and Base class using SQLAlchemy ORM
app_registry: so.registry = so.registry()
Base: Type[so.DeclarativeMeta] = app_registry.generate_base()

# Initialize Flask extensions (SQLAlchemy, Flask-Migrate, LoginManager, Flask-Admin, CSRFProtect)
db = SQLAlchemy()  # Needed for Flask-SQLAlchemy integration
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()
flask_admin = Admin(
    name='Flask Admin',
    url='/flask_admin',  
    template_mode='bootstrap4',  # Use bootstrap4 for compatibility
)

# instantiate flak mail
mail = Mail()

# Create Flask application instance and configure it with the specified configuration settings
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'app_user.login'  # Set the login view for unauthorized users
    csrf.init_app(app)
    flask_admin.init_app(app)
    # Initialize Flask-Mail
    mail.init_app(app)
    
    # User loader function
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(int(user_id))  # Use db.session.query instead of User.query
    
    # Import models and add to Flask-Admin here to avoid circular import
    with app.app_context():
        from .models import User, Content, UserData, Reference, UserFeedback, UserContentState, UserProfile, UserReportTemplate, AdminReportTemplate
        from .admin_views import MyModelView, UserModelView  # Import both MyModelView and UserModelView

    # Register Models in Flask-Admin
    # Register admin-related models with MyModelView
    flask_admin.add_view(MyModelView(Content, db.session, endpoint='contents'))
    flask_admin.add_view(MyModelView(Reference, db.session, endpoint='references'))
    flask_admin.add_view(MyModelView(AdminReportTemplate, db.session, endpoint='admin_report_templates'))

    # Register user-related models with UserModelView
    flask_admin.add_view(ModelView(User, db.session, endpoint='users'))
    flask_admin.add_view(ModelView(UserData, db.session, endpoint='user_data'))
    flask_admin.add_view(ModelView(UserFeedback, db.session, endpoint='user_feedbacks'))
    flask_admin.add_view(ModelView(UserContentState, db.session, endpoint='user_content_states'))
    flask_admin.add_view(UserModelView(UserProfile, db.session, endpoint='user_profiles'))
    flask_admin.add_view(UserModelView(UserReportTemplate, db.session, endpoint='user_report_templates'))

    # Register Blueprints
    # App admin routes
    from .admin_routes import app_admin_bp
    app.register_blueprint(app_admin_bp, url_prefix='/app_admin')
    # Content routes
    from .content_routes import content_routes_bp
    app.register_blueprint(content_routes_bp, url_prefix='/content')  # Register with url_prefix if it's for the content navigation site
    # Main routes
    from .main_routes import main_bp  # Using the corrected variable name
    app.register_blueprint(main_bp)
    # User routes
    from .user_routes import app_user_bp
    app.register_blueprint(app_user_bp, url_prefix='/app_user')  # Register with url_prefix if it's for the content navigation site
    #----------------------------------------------------------------
    # Functions to manage user ideletimout, warning times and session timeouts :
    def update_last_activity():
            session['last_activity'] = datetime.now(timezone.utc)  # Ensure it's timezone-aware

    def check_idle_timeout():
        last_activity = session.get('last_activity')
        idle_timeout = app.config.get('SESSION_IDLE_TIMEOUT')  # Default timeout
        warning_time = app.config.get('SESSION_WARNING_TIME')   # Default warning time
        if last_activity:
            # Make sure the comparison is between timezone-aware datetimes
            time_since_last_activity = datetime.now(timezone.utc) - last_activity
        else:
            time_since_last_activity = timedelta(0)  # Initialize as a timedelta object

        if time_since_last_activity > idle_timeout:
            session.clear()
            flash('You have been logged out due to inactivity.', 'warning')
            return redirect(url_for('app_user.login'))
        elif time_since_last_activity > (idle_timeout - warning_time):
            session['show_warning'] = True
        else:
            session.pop('show_warning', None)
            
# ================================================================
# Functions to be executed before initialization
    @app.before_request
    def handle_before_request():
        if current_user.is_authenticated:
            check_idle_timeout()
            update_last_activity()

    # Important security validations to be performed PRIOR to app startup. 
    @app.before_request
    def restrict_admin_access():
        # Restrict access to Flask-Admin views only to admin users
        if request.path.startswith('/flask_admin'):
            if not (current_user.is_authenticated and current_user.is_admin):
                flash('Admin access required.', 'warning')
                return redirect(url_for('main_routes.index'))
    # Ensure the session is not set to permanent
    @app.before_request
    def make_session_non_permanent():
        session.permanent = False  # Ensures sessions are non-permanent
        
    #Logging
    # Set up basic logging to a file
    log_dir = 'app/logs'
    os.makedirs(log_dir, exist_ok=True)  # Ensure the directory exists
    log_file = os.path.join(log_dir, 'app.log')

    return app