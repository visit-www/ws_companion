# * Imports
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from .models import User, UserContentState, CategoryNames, ModuleNames
from . import db
from .forms import LoginForm  # Import the form class
from config import Config
from datetime import timedelta

# * Blueprint setup
app_user_bp = Blueprint(
    'app_user', __name__,
    static_folder='static',
    static_url_path='/static'
)

#----------------------------------------------------------------
# * Login and Logout routes
#----------------------------------------------------------------

# User Login Route
@app_user_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()  # Instantiate the form
    login_failed = False  # Default value for login_failed
    if form.validate_on_submit():  # Checks if the form is submitted and valid
        username = form.username.data.strip()
        password = form.password.data.strip()
        remember = 'remember' in request.form  # Check if "Remember Me" was selected
        # Query the user using SQLAlchemy's session
        user = db.session.query(User).filter_by(username=username).first()
        if user and user.check_password(password):
            # Set the session to be permanent only if "Remember Me" is checked
            session.permanent = remember
            login_user(user, remember=remember)
            session['user_id'] = user.id  # Manually setting session data
            session.modified = True       # Ensure that session modifications are recognized
            flash(f'Log in succeful! Welcome back {user.username}!<hr style="color:yellow;">', 'success')
            return redirect(url_for('main_routes.index'))
        else:
            login_failed = True
            flash('Login failed.<br>Please check your username and password and try again.', 'danger')

    return render_template('login.html',form=form, login_failed=login_failed)

# Logout route
@app_user_bp.route('/logout')
def logout():
    if not current_user.is_authenticated:
        flash("You must be logged in to log out!", "info")
        return redirect(url_for('app_user.login'))
    
    logout_user()
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('app_user.login'))

# *----------------------------------------------------------------
# User Registration Route
@app_user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        email = request.form['email'].strip()
        
        # Check if the username or email already exists
        existing_user = db.session.query(User).filter_by(username=username).first()
        existing_email = db.session.query(User).filter_by(email=email).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'warning')
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
#* ----------------------------------------------------------------
# Forget / reset passwrod route:
@app_user_bp.route('/credential_management', methods=['GET', 'POST'])
def credential_manager():
    if request.method == 'GET':
        action=request.args.get('action')
        if action=="forgot_password":
            return render_template('credential_manager.html')
    else:
        action=request.form.get('action')
        email=request.form.get('email')
        if action=='retrieve_password':
            user_data=db.session.query(User).filter_by(email=email)
            hash_password=user_data.password
            password=hash_password.strip()
            
            flash(f"user with email= {email} has asked for retrieving the password")
        elif action=='reset_password':
            flash(f'user with email= {email} has asked to reset the password')
        else:
            flash(f"user with email= {email} has asked to retreive the username")
    return render_template('credential_manager.html')

# *----------------------------------------------------------------
# User Profile/Account Page and Related Routes
# *----------------------------------------------------------------

# Route to serve the user_management page
@app_user_bp.route('/account', methods=['GET'])
@login_required
def user_management():
    categories = CategoryNames  # Use Enum to populate the categories select box
    modules = ModuleNames  # Use Enum to populate the modules select box
    return render_template('user_management.html', categories=categories, modules=modules)

# Placeholder routes for profile functionalities

@app_user_bp.route('/upload_profile_pic', methods=['POST'])
@login_required
def upload_profile_pic():
    # Placeholder logic for uploading profile pic
    file = request.files['profile_pic']
    if file:
        # Handle file saving logic
        flash('Profile picture updated successfully!', 'success')
    return redirect(url_for('app_user.user_management'))

@app_user_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    # Placeholder logic for updating email
    email = request.form.get('email')
    current_user.email = email
    db.session.commit()
    flash('Email updated successfully!', 'success')
    return redirect(url_for('app_user.user_management'))

@app_user_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    # Placeholder logic for changing password
    new_password = request.form.get('password')
    current_user.set_password(new_password)
    db.session.commit()
    flash('Password changed successfully!', 'success')
    return redirect(url_for('app_user.user_management'))

@app_user_bp.route('/update_preferences', methods=['POST'])
@login_required
def update_preferences():
    # Placeholder logic for saving preferred categories and modules
    categories = request.form.getlist('categories')
    modules = request.form.getlist('modules')
    # Save preferences to UserContentState or another appropriate place
    flash('Preferences updated successfully!', 'success')
    return redirect(url_for('app_user.user_management'))

@app_user_bp.route('/check_subscription', methods=['GET'])
@login_required
def check_subscription():
    # Placeholder route for checking subscriptions
    flash('Checking subscriptions...', 'info')
    return redirect(url_for('app_user.user_management'))

@app_user_bp.route('/request_content', methods=['POST'])
@login_required
def request_content():
    # Placeholder logic for content request
    content_request = request.form.get('content_request')
    # Handle content request logic
    flash('Content request submitted!', 'success')
    return redirect(url_for('app_user.user_management'))

@app_user_bp.route('/request_music_playlist', methods=['POST'])
@login_required
def request_music_playlist():
    # Placeholder logic for music playlist request
    music_request = request.form.get('music_request')
    # Handle music request logic
    flash('Music playlist request submitted!', 'success')
    return redirect(url_for('app_user.user_management'))

@app_user_bp.route('/add_report_template', methods=['POST'])
@login_required
def add_report_template():
    # Placeholder logic for adding personal report templates
    template_name = request.form.get('report_template')
    # Save to UserContentState or related model
    flash('Report template added successfully!', 'success')
    return redirect(url_for('app_user.user_management'))