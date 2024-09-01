# * Imports
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from sqlalchemy import inspect, Table
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Content, Guideline, UserFeedback, UserData, Reference
from . import db
from .forms import AddContentForm, AddUserForm
import json
import os
import shutil
from datetime import datetime, timezone

# * Blueprint setup
app_admin_bp = Blueprint(
    'app_admin', __name__,
    static_folder='static',
    static_url_path='/static'
)

#todo: Global Error Handling
#@app_admin_bp.errorhandler(Exception)
#def handle_exception(e):
#    app_admin_bp.logger.error(f"Unhandled Exception in Admin Blueprint: {e}", exc_info=True)
#    return jsonify({'error': 'An internal error occurred'}), 500



# * Admin Dashboard Route
@app_admin_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('user.login'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_contents':
            return redirect(url_for('app_admin.add_contents'))
        elif action == 'user_management':
            return redirect(url_for('app_admin.user_management'))
        elif action == 'reset_database':
            return redirect(url_for('app_admin.reset_database'))
        elif action == 'reset_users':
            return redirect(url_for('app_admin.reset_users'))

    users = db.session.query(User).all()
    contents = db.session.query(Content).all()
    
    return render_template('admin_dashboard.html', users=users, contents=contents)

#*----------------------------------------------------------------


# todo: Placeholder route for adding contents
@app_admin_bp.route('/add_contents', methods=['GET', 'POST'])
@login_required
def add_contents():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('user.login'))

    return render_template('add_contents.html')

# todo: Placeholder route for user management
@app_admin_bp.route('/user_management', methods=['GET', 'POST'])
@login_required
def user_management():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('user.login'))

    return render_template('user_management.html')

# todo: Placeholder route for resetting the database
@app_admin_bp.route('/reset_database', methods=['GET', 'POST'])
@login_required
def reset_database():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('user.login'))

    return render_template('reset_database.html')

# todo: Placeholder route for resetting users
@app_admin_bp.route('/reset_users', methods=['GET', 'POST'])
@login_required
def reset_users():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('user.login'))

    return render_template('reset_users.html')

################################################################


# ===================================================================
# Admin Management Routes
# ===================================================================f

# *----------------------------------------------------------------
# Add User Route (Admin Only)
@app_admin_bp.route('/admin/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main_routes.index'))

    form = AddUserForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(
            username=form.username.data,
            password=hashed_password,
            is_admin=form.is_admin.data,
            is_paid=form.is_paid.data
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('New user added successfully.', 'success')
            return redirect(url_for('app_admin.admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('app_admin.add_user'))

    return render_template('add_users.html', form=form)

# *----------------------------------------------------------------
