# * Imports
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify,send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash,check_password_hash
from .models import User, UserContentState, CategoryNames, ModuleNames,UserData,UserProfile,UserFeedback,UserReportTemplate
from . import db
from .forms import LoginForm  # Import the form class
from config import Config
from datetime import timedelta, datetime, timezone
from flask_mail import Message
from . import mail  # Import the mail instance from your app initialization
from .util import generate_password_reset_token,verify_password_reset_token, generate_otp_secret,generate_otp_token
from datetime import datetime, timezone
import os
import shutil
from config import basedir,userdir
from werkzeug.utils import secure_filename
# * Blueprint setup
app_user_bp = Blueprint(
    'app_user', __name__,
    static_folder='static',
    static_url_path='/static'
)

# ----------------------------------------------------------------
# * Route t degenerate qr code for 2factor authentication:
# ----------------------------------------------------------------
from .util import load_default_data,add_default_admin,add_default_contents,add_anonymous_user
import pyotp
import qrcode
import io
@app_user_bp.route('/qrcode')
@login_required
def qrcode_route():
    totp_secret = session.get('totp_secret')
    if not totp_secret:
        return 'TOTP secret not found.', 400

    # Use the user's email as the identifier
    user_identifier = current_user.email

    # Generate the provisioning URI
    totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(name=user_identifier, issuer_name='WSCompanion')

    # Generate QR code image
    img = qrcode.make(totp_uri)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


# ----------------------------------------------------------------
# * enale 2fa:
#---------------------------------------------------------------
@app_user_bp.route('/enable_2fa')
@login_required  # Ensure the user is logged in
def enable_2fa():
    # Generate and store the TOTP secret
    totp_secret = pyotp.random_base32()
    session['totp_secret'] = totp_secret
    return render_template('enable_2fa.html', totp_secret=totp_secret)
# ----------------------------------------------------------------
# * enale 2fa:
#---------------------------------------------------------------
@app_user_bp.route('/disable_2fa', methods=['POST'])
@login_required
def disable_2fa():
    user = current_user  # Assuming you have `current_user` from Flask-Login
    user.totp_secret = None
    db.session.commit()
    flash('Two-Factor Authentication has been disabled.', 'success')
    return redirect(url_for('app_user.user_management'))


# ----------------------------------------------------------------
# * verify qr code route 
#----------------------------------------------------------------
@app_user_bp.route('/verify_2fa', methods=['POST'])
@login_required
def verify_2fa():
    token = request.form.get('token')
    totp_secret = session.get('totp_secret')

    if not totp_secret:
        flash('TOTP secret not found.', 'danger')
        return redirect(url_for('app_user.user_management'))

    totp = pyotp.TOTP(totp_secret)
    if totp.verify(token):
        # Save the totp_secret to the user's record
        user = current_user
        user.totp_secret = totp_secret
        db.session.commit()
        session.pop('totp_secret', None)
        flash('Two-Factor Authentication has been enabled.', 'success')
        return redirect(url_for('app_user.user_management'))
    else:
        flash('Invalid token. Please try again.', 'danger')
        return redirect(url_for('app_user.enable_2fa'))


#----------------------------------------------------------------
# * Login and Logout routes
#----------------------------------------------------------------

# User Login Route
@app_user_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()  # Instantiate the form
    login_failed = False  # Default value for login_failed
    if form.validate_on_submit():  # Checks if the form is submitted and valid
        username = form.username.data.strip().lower()
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
            user.status='active' 
            # Update UserData fields
            user_data = db.session.query(UserData).filter_by(user_id=user.id).first()
            if user_data:
                user_data.last_interaction = datetime.now(timezone.utc)
                # Copy current login to last login
                if user_data.current_login:
                    user_data.last_login = user_data.current_login
                # Update current login to the new login time
                user_data.current_login = datetime.now(timezone.utc)
                if user_data.login_count is None:
                    user_data.login_count = 0
                user_data.login_count += 1
                user_data.interaction_type = "logged_in"  # Ensure this value aligns with your enum or model definition
                user_data.last_interaction=datetime.now(timezone.utc)
                user.status = "active"
                db.session.commit()  # Save changes to the database
            
            print(f'Log in successful! Welcome back {user.username}!<hr style="color:yellow;">', 'success')
            return redirect(url_for('main_routes.index'))
        else:
            login_failed = True
            flash('Login failed.<br>Please check your username and password and try again.', 'danger')

    return render_template('login.html', form=form, login_failed=login_failed)
# Logout route
@app_user_bp.route('/logout')
@login_required
def logout():
    # Ensure the user is authenticated
    if not current_user.is_authenticated:
        flash("You must be logged in to log out!", "info")
        return redirect(url_for('app_user.login'))

    # Update user data before logging out
    user_id = current_user.id
    user = db.session.query(User).filter_by(id=user_id).first()
    user_data = db.session.query(UserData).filter_by(user_id=user_id).first()

    if user and user_data:
        # Ensure last_login is not None
        if user_data.last_login and user_data.session_start_time is not None:
            # Ensure last_login is timezone-aware
            if user_data.last_login.tzinfo is None:
                user_data.last_login = user_data.last_login.replace(tzinfo=timezone.utc)
            elif user_data.current_login is None:
                user_data.current_login=user_data.current_login.replace(tzinfo=timezone.utc)
            # Calculate the time spent since last login
            time_spent = datetime.now(timezone.utco) - user_data.current_login
            time_spent_in_minutes = time_spent.total_seconds()/60
            # Prevent negative time_spent
            if time_spent_in_minutes < 0:
                user_data.time_spent = 0
            else:
                user_data.time_spent += time_spent_in_minutes
        else:
            # If session_start_time is None, we can't calculate time_spent
            # Optionally, you can set time_spent to zero or handle it as needed
            user_data.time_spent += 0

        # Update user data
        user_data.last_interaction = datetime.now(timezone.utc)
        user_data.interaction_type = "logged_out"  # Corrected typo from 'loged_out' to 'logged_out'
        user.status = "inactive"  # Set user status to inactive

        # Commit the changes to the database
        db.session.commit()

    # Log the user out
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
        retyped_password = request.form['retyped_password'].strip()
        email = request.form['email'].strip()

        # Check if retyped and primary password match
        if password != retyped_password:
            flash('Passwords do not match. Please retype them correctly.', 'warning')
            return redirect(url_for('app_user.register'))

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
            try:
                # Create and add the new user
                hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                new_user = User(username=username.lower(), password=hashed_password, email=email.lower())
                db.session.add(new_user)
                db.session.commit()

                # Define the paths for the dummy profile picture and the target location
                dummy_profile_pic_path = os.path.join(basedir,'app','static', 'assets','images','dummy_profile_pic.png')
                profile_pic_folder = os.path.join(userdir, f"{new_user.id}",'profile_pic')
                profile_pic_path = os.path.join(profile_pic_folder, 'dummy_profile_pic.png')

                # Create the target directory if it doesn't exist
                os.makedirs(profile_pic_folder, exist_ok=True)

                try:
                    # Copy the dummy profile picture to the target directory
                    shutil.copy(dummy_profile_pic_path, profile_pic_path)
                except Exception as e:
                    flash(f'Error copying the dummy profile picture: {str(e)}', 'danger')
                    print(f'Error copying the dummy profile picture: {str(e)}')

                # Initialize UserProfile with default values, using lists instead of JSON
                profile = UserProfile(
                    user_id=new_user.id,
                    profile_pic='dummy_profile_pic.png',  # This should just be the file name
                    profile_pic_path=profile_pic_path,  # This is the full path to where the file is stored
                    preferred_categories=','.join([category.value for category in CategoryNames]),  # Store as comma-separated string
                    preferred_modules=','.join([module.value for module in ModuleNames]),  # Store as comma-separated string
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.session.add(profile)

                # Initialize UserData with baseline information
                user_data = UserData(
                    user_id=new_user.id,
                    interaction_type='registered',
                    feedback=None,
                    content_rating=None,
                    time_spent=0,
                    last_interaction=datetime.now(timezone.utc),
                    current_login=datetime.now(timezone.utc),  # Assume the user has just logged in
                    last_login=None,
                    session_start_time=None,
                    login_count=0
                )
                db.session.add(user_data)

                # Initialize UserContentState with baseline information
                user_content_state = UserContentState(
                    user_id=new_user.id,
                    modified_filepath=None,
                    annotations=None,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.session.add(user_content_state)

                # Commit all changes to the database
                db.session.commit()

                # Clear the session and login the new user
                session.clear()  # Clears the existing session data to avoid conflicts
                login_user(new_user)  # Logs in the newly created user, ensuring the session reflects the correct user
                flash('Registration successful! Profile and related data initialized. Please log in.', 'success')
                return redirect(url_for('app_user.user_management'))

            except Exception as e:
                # Rollback any changes if an error occurs
                db.session.rollback()
                flash(f'Registration failed due to an error: {str(e)}', 'danger')
                print(f'Registration failed due to an error: {str(e)}')
                return redirect(url_for('app_user.register'))  # Corrected to redirect to the registration page

        else:
            flash('All fields are required.', 'danger')

    return render_template('register.html')
# *----------------------------------------------------------------
# Forget username / reset passwrod route:
@app_user_bp.route('/credential_management', methods=['GET', 'POST'])
def credential_manager():
    if request.method == 'GET':
        action=request.args.get('action')
        if action=="forgot_password":
            return render_template('credential_manager.html')
    else:
        action=request.form.get('action')
        input_email=request.form.get('email')
        input_email=input_email.lower()
        user=db.session.query(User).filter_by(email=input_email).first()
        if user:
            user_email=user.email
            if action=='reset_password':
                try:
                    # Generate the password reset token
                    token = generate_password_reset_token({'email': user_email})
                    
                    # Create the reset link
                    reset_link = url_for('app_user.change_password', token=token, _external=True, _scheme='https')
                    
                    # Prepare the email message for password reset
                    msg = Message('Account Recovery Email from WS Companion', recipients=[user_email])
                    msg.html = render_template('reset_password_email.html', reset_link=reset_link)
                    msg.body = render_template('reset_password_email.txt', reset_link=reset_link)
                    # Send the email
                    mail.send(msg)
                    
                    flash('A password reset link has been sent to your email successfully!<hr>This link is valid only for 10 minutes.', 'success')
                    return redirect(url_for('app_user.login'))
                except Exception as e:
                    print(f'Failed to send test email: {str(e)}')
                    flash(f'Failed to send test email: {str(e)}', 'danger')
                    return redirect(url_for('app_user.credential_manager'))
            else: # implies the action must be retrieve_username
                try:
                    # Prepare the email message for username retrieval
                    msg = Message('Account Recovery Email from WS Companion', recipients=[user_email])
                    msg.html = render_template('retrieve_username_email.html', user=user)
                    msg.body = render_template('retrieve_username_email.txt', user=user)
                    mail.send(msg)
                    flash('An account recovery email has been sent to your email address successfully!', 'success')
                    return redirect(url_for('app_user.login'))
                except Exception as e:
                    print(f'Failed to send test email: {str(e)}')
                    flash(f'Failed to send test email: {str(e)}', 'danger')
                    return redirect(url_for('app_user.credential_manager'))
        else:
            flash(f'No user found with this email address! <hr> Please enter the email assocaited with your account.', 'danger')
            return redirect(url_for('app_user.credential_manager'))
    return render_template('credential_manager.html')

# Change Password Route
@app_user_bp.route('/change_password/<token>', methods=['GET', 'POST'])
def change_password(token):
    # If POST request, process the form
    if request.method == 'POST':
        # Get form data
        password = request.form.get('password')
        retyped_password = request.form.get('retyped-password')
        
        # Validate passwords match
        if password != retyped_password:
            flash('Passwords do not match. Please try again.', 'danger')
            return render_template('change_password.html', token=token)
        
        # Verify token and update password
        user_data = verify_password_reset_token(token)
        if not user_data:
            flash('The reset link is invalid or expired. Please try again.', 'danger')
            return redirect(url_for('app_user.credential_manager'))
        
        # Assume user_data contains email
        user = db.session.query(User).filter_by(email=user_data.get('email')).first()
        if not user:
            flash('No account associated with this email.', 'danger')
            return redirect(url_for('app_user.credential_manager'))
        
        # Update the user's password securely
        user.set_password(password)  # This method should hash the password before saving
        db.session.commit()
        
        flash('Your password has been reset successfully! You can now log in with your new password.', 'success')
        return redirect(url_for('app_user.login'))
    
    # Render the change password form
    return render_template('change_password.html', token=token)
# ********************************
# Update password route:
@app_user_bp.route('/update_password', methods=['GET', 'POST'])
@login_required
def update_password():
    if request.method == 'POST':
        # Get form data
        new_password = request.form.get('new-password')
        retyped_password = request.form.get('retyped-password')
        
        if new_password:
            # Validate new passwords match
            if new_password != retyped_password:
                flash('Passwords do not match. Please try again.', 'danger')
                return render_template('user_management.html')
    
            # Check if new password is different from current
            if current_user.check_password(new_password):
                flash('You are attempting to reuse your old password. Please enter a new password.', 'danger')
                return render_template('user_management.html')
    
            # Update the password securely
            try:
                current_user.set_password(new_password)  # Hashing the password
                db.session.commit()
                flash('Your password has been updated successfully!', 'success')
                return redirect(url_for('app_user.user_management'))
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred while updating your password: {str(e)}', 'danger')
                return redirect(url_for('app_user.user_management'))
        else:
            flash('You did not enter any passwords.', 'danger')

    return render_template('user_management.html')

# Chanage email route:
@app_user_bp.route('/confirm_email')
@login_required
def confirm_email():
    token = request.args.get('token')
    if not token:
        flash('Invalid or missing token.', 'danger')
        return redirect(url_for('app_user.user_management'))
    token_data = verify_password_reset_token(token)
    if token_data and 'email' in token_data:
        new_email = token_data['email']
        # Update the user's email
        try:
            current_user.email = new_email
            db.session.commit()
            flash('Your email has been updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while updating your email. Please try again.', 'danger')
        return redirect(url_for('app_user.user_management'))
    else:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('app_user.user_management'))

# ! Account recovery opetions:
@app_user_bp.route('/recover_account', methods=['GET', 'POST'])
def recover_account():
    if request.method == 'POST':
        recovery_option = request.form.get('recovery_option')
        if recovery_option == 'phone':
            phone = request.form.get('phone')
            user = db.session.query(User).filter_by(phone=phone).first()
            if not user:
                flash('No account associated with this phone number.', 'danger')
                return redirect(url_for('app_user.recover_account'))
            # Send a token via SMS using your SMS service (Twilio, etc.)
            token = generate_password_reset_token(user.email)
            send_sms(phone, f'Your account recovery token: {token}')
            flash('A recovery token has been sent to your phone.', 'success')
            return redirect(url_for('app_user.verify_recovery_token'))

        elif recovery_option == 'recovery_email':
            email = request.form.get('email')
            user = db.session.query(User).filter_by(email=email).first()
            if not user:
                flash('No account associated with this recovery email.', 'danger')
                return redirect(url_for('app_user.recover_account'))
            # Send a token via email using your mail extension
            token = generate_password_reset_token(user.email)
            send_email(user.email, 'Account Recovery', f'Your account recovery token: {token}')
            flash('A recovery token has been sent to your email.', 'success')
            return redirect(url_for('app_user.verify_recovery_token'))

        elif recovery_option == 'authenticator':
            # Assuming you have 2FA set up already
            if current_user.is_authenticated and current_user.two_factor_enabled:
                flash('You can use your authenticator app to verify and recover your account.', 'success')
                return redirect(url_for('app_user.verify_recovery_token'))
            else:
                flash('No authenticator app is set up for this account.', 'danger')
                return redirect(url_for('app_user.recover_account'))
    
    # Render the recovery form if GET request
    return render_template('recover_account.html')


# *----------------------------------------------------------------
# User Profile/Account Page and Related Routes
# *----------------------------------------------------------------
# Route to serve the user_management page
@app_user_bp.route('/account', methods=['GET'])
@login_required
def user_management(): 
    categories = CategoryNames  # Enum to populate the categories select box
    modules = ModuleNames  # Enum to populate the modules select box
    # Fetch the current user's profile
    user_profile = db.session.query(UserProfile).filter_by(user_id=current_user.id).first()
    try:
        if user_profile:
            if user_profile.profile_pic:
                # Construct the relative path for the profile picture
                profile_pic_rel_path = f"{current_user.id}/profile_pic/{user_profile.profile_pic}"

                # Generate URL to serve the profile picture using the `serve_user_data` route
                profile_pic_path = url_for('serve_user_data', filename=profile_pic_rel_path)
            else:
                # Use the default profile picture if `profile_pic` is missing
                profile_pic_path = url_for('static', filename='assets/images/logo-white-bg.pngg')
            
            print(f"Profile picture path: {profile_pic_path}")
            # Embed email verification status.
            return render_template('user_management.html', categories=categories, modules=modules, profile_pic_path=profile_pic_path)
    
        else:
            # Fall-back to the default profile picture if no user profile exists
            return render_template('user_management.html', categories=categories, modules=modules, profile_pic_path=url_for('static', filename='assets/images/logo-white-bg.png'))

    except Exception as e:
        # Handle any unexpected errors gracefully, log the error, and fall back to the default profile picture
        print(f"An error occurred: {e}")
        return render_template('user_management.html', categories=categories, modules=modules, profile_pic_path=url_for('static', filename='assets/images/logo-white-bg.png'))
# .###############################
# PROFILE MANAGEMENT ROUTES
# ===============================

@app_user_bp.route('/profile_manager', methods=['GET', 'POST'])
@login_required
def profile_manager():
    if request.method == 'POST':
        action = request.form.get('action')
        username = current_user.username
        user_id = current_user.id

        if action == 'update_profile_pic':
            
            # Handle profile picture upload logic here
            pic = request.files.get('profile_pic')  # Correctly get the file from the request
            if pic:
                filename = secure_filename(pic.filename)
                target_folder = os.path.join(basedir, userdir, f"{user_id}",'profile_pic')
                os.makedirs(target_folder, exist_ok=True)  # Create the directory if it doesn't exist
                profile_pic_path = os.path.join(target_folder, filename)

                try:
                    # Save the uploaded picture
                    pic.save(profile_pic_path)

                    # Update the user profile in the database
                    user = db.session.query(UserProfile).filter_by(user_id=current_user.id).first()
                    old_pic = user.profile_pic
                    old_pic_path = user.profile_pic_path
                    archived_folder = os.path.join(basedir, 'archived', f"{user_id}",'profile_pic')
                    os.makedirs(archived_folder, exist_ok=True)
                    if "dummy" in old_pic:
                        try:
                            os.remove(old_pic_path)
                        except FileNotFoundError:
                            pass  # Ignore the error if the file doesn't exist (e.g., it was already deleted)

                    elif old_pic and "dummy" not in old_pic:
                        shutil.move(old_pic_path, archived_folder)  # Archive the old profile picture

                    # Update the profile picture path in the user's profile
                    user.profile_pic = filename
                    user.profile_pic_path = profile_pic_path
                    user.updated_at = datetime.now(timezone.utc)

                    # Update the user data
                    user_data = db.session.query(UserData).filter_by(user_id=current_user.id).first()
                    if user_data:
                        user_data.interaction_type = "updated_profile_pic"
                        user_data.last_interaction = datetime.now(timezone.utc)

                    db.session.commit()  # Commit the changes to the database
                    flash('Profile picture uploaded successfully!', 'info')
                except Exception as e:
                    db.session.rollback()  # Rollback the session on error
                    flash(f'An error occurred while uploading the profile picture: {e}', 'danger')
                    return redirect(url_for('app_user.profile_manager'))

                # Pass target_folder and filename to the redirected route for rendering
                return redirect(url_for('app_user.user_management'))
            
            else:
                flash('No profile picture uploaded.', 'warning')
                return redirect(url_for('app_user.profile_manager'))

        elif action == 'update_username':
            requested_username = request.form.get('username')
            if requested_username:
                if requested_username == current_user.username:
                    flash('Did you enter your existing username by mistake? Please choose a different username.', 'warning')
                else:
                    # Check if the requested username is already taken
                    existing_user = db.session.query(User).filter_by(username=requested_username).first()
                    if existing_user:
                        flash('Username already taken. Please choose a different username.', 'warning')
                    else:
                        try:
                            current_user.username = requested_username.lower()
                            user_data = db.session.query(UserData).filter_by(user_id=current_user.id).first()
                            user_data.last_interaction = datetime.now(timezone.utc)
                            user_data.interaction_type = "updated_username"
                            db.session.commit()  # Commit the changes to the database
                            flash('Username updated successfully!', 'info')
                            return redirect(url_for('app_user.user_management'))
                        except Exception as e:
                            db.session.rollback()  # Rollback the session on error
                            flash(f'An error occurred while updating the username: {e}', 'danger')
            else:
                flash('No username entered. Please enter a username.', 'warning')
            return redirect(url_for('app_user.profile_manager'))
    
        elif action == 'update_email':
            requested_email = request.form.get('email')
            # Check if the email is different
            if requested_email == current_user.email:
                flash('You have entered your current email. Please enter a new email.', 'warning')
            else:
                # Check if the email is already in use
                existing_user = db.session.query(User).filter_by(email=requested_email).first()
                if existing_user:
                    flash('This email is already in use. Please choose a different email.', 'warning')
                else:
                    # Generate token with the new email
                    token = generate_password_reset_token({'email': requested_email})
                    # Create the confirmation link
                    confirm_link = url_for('app_user.confirm_email', token=token, _external=True)
                    # Send confirmation email
                    print(f"message will be sent to {requested_email}")
                    msg = Message('Confirm Your Email Change', recipients=[requested_email])
                    msg.html = render_template('confirm_email.html', confirm_link=confirm_link)
                    msg.body = render_template('confirm_email.txt', confirm_link=confirm_link)
                    mail.send(msg)
                    flash('A confirmation email has been sent to your new email address. Please check your email. Please note that this link is valid only for 10 minutes.', 'info')
                    return redirect(url_for('app_user.user_management'))
                        
        elif action=="add_recovery_phone":
            recovery_phone = request.form.get('recovery_phone')
            if recovery_phone:
                try:
                    current_user.recovery_phone = recovery_phone
                    db.session.add(current_user)
                    db.session.commit()
                    db.session.commit()
                    user=db.session.query(User).filter_by(id=current_user.id).first()
                    user_email=user.email
                    user_name=user.username
                    account_update_type="Added Recovery Phone"
                    #send intimation to the user that a recovery phone has been added.
                    #create reset link to secure accunt :
                        # Generate the password reset token
                    token = generate_password_reset_token({'email': user_email})
                    
                    # Create the reset link
                    reset_link = url_for('app_user.change_password', token=token, _external=True, _scheme='https')
                    
                    msg=Message("Important: Suspicious activity on your ws-companion account", recipients=[user_email])
                    msg.html = render_template('account_updates_email.html',user_name=user_name,account_update_type=account_update_type,recovery_phone=recovery_phone,reset_link=reset_link)
                    msg.body = render_template('account_updates_email.txt', reset_link=reset_link)
                    mail.send(msg)
                    flash('Recovery phone number added successfully!', 'info')
                except Exception as e:
                    db.session.rollback()  # Rollback the session on error
                    flash(f'An error occurred while updating the recovery phone number: {e}', 'danger')
                    user=db.session.query(User).filter_by(id=current_user.id).first()
            else:
                flash('Please enter a valid recovery phone number')
            pass

    categories = CategoryNames
    modules = ModuleNames
    return render_template('user_management.html')

@app_user_bp.route('/delete_account')
def delete_account():
    flash('this will delete your account permanently')
    return ("This route of handle account deletion initiated by user")



# ===============================
# FINANCE MANAGEMENT ROUTES
# ===============================

@app_user_bp.route('/finance_manager', methods=['GET', 'POST'])
@login_required
def finance_manager():
    # Placeholder for finance-related actions
    if request.method == 'POST':
        # Handle finance management logic here
        flash('Finance management functionality will be implemented here.', 'info')
    return render_template('finance_manager.html')

# Removed individual finance routes like check_subscription as they are now covered by finance_manager.

# ===============================
# SECURITY MANAGEMENT ROUTES
# ===============================

@app_user_bp.route('/security_manager', methods=['GET', 'POST'])
@login_required
def security_manager():
    # Placeholder for security settings management (update questions, setup authenticator)
    if request.method == 'POST':
        # Handle security management logic here
        flash('Security management functionality will be implemented here.', 'info')
    return render_template('account_security.html')

