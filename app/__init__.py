from flask import Flask, jsonify, request, redirect, url_for, flash
from flask_login import current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager
import sqlalchemy.orm as so
from typing import Type
import logging
import os


# Initialize the registry and Base class using SQLAlchemy ORM
registry_manager: so.registry = so.registry()
Base: Type[so.DeclarativeMeta] = registry_manager.generate_base()

# Initialize Flask extensions
db = SQLAlchemy()  # Needed for Flask-SQLAlchemy integration
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'app_user.login'  # Set the login view for unauthorized users
    flask_admin = Admin(app,
        name='Flask Admin',
        url='/flask_admin',  
        template_mode='bootstrap4',  # Use bootstrap4 for compatibility
        
    )
    
    
    # User loader function
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(int(user_id))  # Use db.session.query instead of User.query

    # Register Models in Flask-Admin
    from .models import User, Guideline, Content, UserData, Reference
    flask_admin.add_view(ModelView(User, db.session))  # Add User model to Flask-Admin
    flask_admin.add_view(ModelView(Guideline, db.session))  # Add Guideline model to Flask-Admin
    flask_admin.add_view(ModelView(Content, db.session))  # Add Content model to Flask-Admin
    flask_admin.add_view(ModelView(UserData, db.session))  # Add UserData model to Flask-Admin
    flask_admin.add_view(ModelView(Reference, db.session))  # Add Reference model to Flask-Admin
    
    # Register Blueprints
    from .admin_routes import app_admin_bp
    app.register_blueprint(app_admin_bp, url_prefix='/app_admin')
    
    from .content_routes import nav_bp
    app.register_blueprint(nav_bp, url_prefix='/content')  # Register with url_prefix if it's for the content navigation site
    
    from .routes import bp  # Import the main blueprint
    app.register_blueprint(bp)  # Register without url_prefix if it's for the main site

    from .main_routes import main_bp  # Using the corrected variable name
    app.register_blueprint(main_bp)

    from .user_routes import app_user_bp
    app.register_blueprint(app_user_bp, url_prefix='/app_user')  # Register with url_prefix if it's for the content navigation site
    
    # Set up basic logging to a file
    log_dir = 'app/logs'
    os.makedirs(log_dir, exist_ok=True)  # Ensure the directory exists
    log_file = os.path.join(log_dir, 'app.log')

    with app.app_context():
        from . import models  # Import models to ensure they are registered with SQLAlchemy
    @app.before_request
    
    def restrict_admin_access():
        print("check access")
        # Restrict access to Flask-Admin views only to admin users
        if request.path.startswith('/flask_admin'):
            if not (current_user.is_authenticated and current_user.is_admin):
                flash('Admin access required.', 'warning')
                return redirect(url_for('main_routes.index'))

    return app