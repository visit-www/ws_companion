from flask import Flask, jsonify

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager
import sqlalchemy.orm as so
from typing import Type
import logging
import os

# Initialize the registry and Base class using Sqlalchemy ORM
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
    login_manager.login_view = 'user.login'  # Set the login view for unauthorized users

    # User loader functionadmiadmin_bp_loaderp_loader
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(int(user_id))  # Use db.session.query instead of User.query

    # Register Blueprints
    from .admin_routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    # Register content_navigation Blueprint
    from .content_routes import nav_bp
    app.register_blueprint(nav_bp, url_prefix='/content')  # Register with url_prefix if it's for the content navigation site
    
    # Register the main blueprint
    from .routes import bp  # Import the main blueprint
    app.register_blueprint(bp)  # Register without url_prefix if it's for the main site

    # Import main_bp from main_routes.py
    from .main_routes import main_bp  # Using the corrected variable name
    app.register_blueprint(main_bp)
    
    # Import and register user_bp
    from .user_routes import user_bp
    app.register_blueprint(user_bp, url_prefix='/content')  # Register with url_prefix if it's for the content navigation site
    
    

    # Set up basic logging to a file
    log_dir = 'app/logs'
    os.makedirs(log_dir, exist_ok=True)  # Ensure the directory exists
    log_file = os.path.join(log_dir, 'app.log')
#----------------------------------------------------------------
# todo: loging function to be activated once in prodcution phase only as it is intefering with console debugging durng devleopment. 
#    # Create a file handler
#    file_handler = logging.FileHandler(log_file)
#    file_handler.setLevel(logging.INFO)  # Set to INFO to capture both ERROR and INFO levels
#    file_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
#    file_handler.setFormatter(file_formatter)
#
#    # Create a console handler
#    console_handler = logging.StreamHandler()
#    
#    # Check if the app is in debug mode
#    if app.debug:
#        console_handler.setLevel(logging.DEBUG)  # Show debug logs in the console
#    else:
#        console_handler.setLevel(logging.INFO)   # Show info level logs in production
#
#    console_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
#    console_handler.setFormatter(console_formatter)
#
#    # Get the root logger and add both handlers
#    logger.addHandler(console_handler) 
#    logger = logging.getLogger()
#    logger.setLevel(logging.INFO)  # Set the overall logging level
#    logger.addHandler(file_handler)
#-----------------------------------------------------------------


    with app.app_context():
        from . import models  # Import models to ensure they are registered with SQLAlchemy

    return app