# * Imports
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify

from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Content, Guideline, UserFeedback, UserData, Reference
from . import db
from .forms import UploadForm
import json
import os
import shutil
from datetime import datetime, timezone

# * Blueprint setup
app_user_bp = Blueprint(
    'app_user', __name__,
    static_folder='static',
    static_url_path='/static'
)

#todo: Global Error Handling
#@app_user_bp.errorhandler(Exception)
#def handle_exception(e):
#    app_user_bp.logger.error(f"Unhandled Exception in Admin Blueprint: {e}", exc_info=True)
#    return jsonify({'error': 'An internal error occurred'}), 500

#----------------------------------------------------------------
#----------------------------------------------------------------
    # * Login and Logout routes
#----------------------------------------------------------------

# User Login Route
@app_user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        # Query the user using SQLAlchemy's session
        user = db.session.query(User).filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Login successful! Welcome back.', 'success')
            return redirect(url_for('main_routes.index'))
        else:
            flash('Login failed. Please check your username and password and try again.', 'danger')

    return render_template('login.html')

# Logout route
@app_user_bp.route('/logout')

def logout():
    if not current_user.is_authenticated:   # Ensure user is logged in before allowing access to this route (not using @loginreuired to allow felxible messaging)
        flash("You must be logged in to log out!", "info")
        return redirect(url_for('app_user.login'))
    # debug statements
    print('calling logout function')
    logout_user()
    flash('You have been succefuly logged out.', 'info')
    return redirect(url_for('app_user.login'))
# *----------------------------------------------------------------

# User Registration Route
@app_user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        email = request.form['email'].strip()
        
        # Check if the username already exists
        existing_user = db.session.query(User).filter_by(username=username).first()
        existing_email = db.session.query(User).filter_by(email=email).first()
        if existing_user:
            flash('Username  already exists. Please choose a different one.', 'warning')
            return redirect(url_for('app_user.register'))
        elif existing_email:
            flash('Email already registered. Please choose a different one.', 'warning')
            return redirect(url_for('app_user.register'))
        
        if username and password and email:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, password=hashed_password, email=email)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('app_user.login'))
        else:
            flash('All fields are required.', 'danger')
    
    return render_template('register.html')