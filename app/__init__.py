from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_login import LoginManager
import sqlalchemy.orm as so
from typing import Type

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
    login_manager.login_view = 'main.login'  # Set the login view for unauthorized users

    # User loader function
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(int(user_id))  # Use db.session.query instead of User.query

    # Register Blueprints
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        from . import models  # Import models to ensure they are registered with SQLAlchemy

    return app