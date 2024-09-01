# * Imports
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify
from sqlalchemy import inspect, Table,MetaData
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Content, Guideline, UserFeedback, UserData, Reference
from . import db, Base
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
# View all the models/tables in one place :
@app_admin_bp.route('/models')
@login_required
def view_models():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main_routes.index'))
    
    # Use the Base metadata to get all model (table) names
    model_names = Base.metadata.tables.keys()
    endpoints = {
        'users': 'users',
        'guidelines': 'guidelines',
        'contents': 'contents',
        'user_data': 'user_data',
        'references': 'references',
        'user_feedback': 'user_feedback',
    }
    # Example for getting data from one model; adjust this part based on your exact needs
    tables_data = []
    for table_name in model_names:
        if not table_name=='guidelines': # todo: temprorary line - delete this when guidelines model is removed
            # Reflect the table from the metadata
            table = Base.metadata.tables[table_name]
            # Perform a query to get data from the table; adapt 'db.session' usage based on your DB setup
            rows = db.session.execute(table.select()).fetchall()  # Fetch all rows from the table
            endpoint=endpoints[table_name]
            # Append data for each table to list
            tables_data.append({
                'table_name': table_name,
                'rows': rows,
                'table': table,
                'getattr': getattr,
                'endpoint': endpoint
            })

    # Pass the list of tables data to the template
    return render_template('tables.html', tables_data=tables_data)
#*----------------------------------------------------------------
@app_admin_bp.route('/manage-model', methods=['GET', 'POST'])
@login_required
def manage_model():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main_routes.index'))

    # Get the action and button ID from the form
    action = request.form.get('action')
    button_id = request.form.get('button_id')

    # Use the Base metadata to get all model (table) names
    model_names = Base.metadata.tables.keys()
    if action == "add_data" and button_id in model_names:
        # If action is 'add_data' and button ID matches a model name, redirect to the correct URL
        # Construct the URL to add new entries to the model via Flask-Admin
        target_url = f"/flask_admin/{button_id}/new/"
        return redirect(target_url)
    # ! Debugging 
    # If no specific action matches, render the test page with tables data and message in console
    return render_template(url_for('main_routes.debug'))
# *----------------------------------------------------------------
# todo: Placeholder route for adding contents
@app_admin_bp.route('/reset_database', methods=['GET', 'POST'])
@login_required
def reset_db():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('app_user.login'))
    
    # Safely retrieve form data with error handling
    action = request.form.get('action', '')
    button_id = request.form.get('button_id', '')
    
    # Fetch all model names (table names) from SQLAlchemy's metadata
    model_names = Base.metadata.tables.keys()
    print(model_names)
    
    if action == "reset_users" and button_id == "users":
        print(f"action is {action}")
        for table_name in model_names:
            if table_name == 'users':
                # Ensure to fetch users table and preserve admins
                user_table = Table(table_name, MetaData(), autoload_with=db.engine)
                query = db.session.query(user_table).filter(user_table.c.is_admin == False)
                # Delete non-admin users
                query.delete(synchronize_session=False)
                db.session.commit()
        flash("All users except admins deleted.", 'warning')
        return redirect('/flask_admin/users')
    
    elif action == 'reset_db' and button_id == 'db':
        flash("The resetting of the database is not enabled. Please contact the owner of the App if you want to perform this action.", 'warning')
        # Corrected line: added parentheses around url_for
        return redirect(url_for('app_admin.view_models'))
#!----------------------------------------------------------------