from flask import Blueprint, render_template, request, redirect, url_for, flash,session, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User,Content,Guideline, UserData,UserFeedback,Reference
from . import db
from .forms import AddGuidelineForm, AddUserForm
import os
import json
from flask import Blueprint, render_template, send_from_directory, request, redirect, url_for, flash
from sqlalchemy import inspect, Table
import sqlalchemy as sa
import shutil
from datetime import datetime, timezone
#----------------------------------------------------------------
# Blueprint configuration
bp = Blueprint(
    'main', __name__,
    static_folder='static',
    static_url_path='/static'
)

# *===================================================================
# User Management Routes
# *==================================================================
# ! These routes moved to user_routes.py

# ===================================================================
# Admin Management Routes
# ===================================================================

# *----------------------------------------------------------------
# Add User Route (Admin Only)
@bp.route('/admin/add_user', methods=['GET', 'POST'])
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
            return redirect(url_for('main.add_user'))

    return render_template('add_users.html', form=form)

# *----------------------------------------------------------------

# * Route to view specific table data
@bp.route('/admin/db_tables/view/<table_name>')
@login_required
def view_table_data(table_name):
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main_routes.index'))

    # Reflect the table from the database
    table = Table(table_name, db.metadata, autoload_with=db.engine)

    # Fetch all data from the table
    query = db.session.query(table).all()

    # Pass both the rows, the table metadata, and getattr to the template
    return render_template('view_table_data.html', table_name=table_name, rows=query, table=table, getattr=getattr)

# *----------------------------------------------------------------
# Route to reset users

@bp.route('/admin/reset_users')
@login_required
def reset_users():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main_routes.index'))

    # Delete all users from the database
    db.session.query(User).delete()#-
    db.session.query(User).delete()  # Fixed the model name from 'User' to 'User'#+
    db.session.commit()
    flash('All users have been reset successfully!', 'success')

# *----------------------------------------------------------------
# Route to delete a row from a specific table
@bp.route('/admin/db_tables/delete/<table_name>/<int:row_id>', methods=['POST'])
@login_required
def delete_row(table_name, row_id):
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main_routes.index'))

    # Reflect the table from the database
    table = Table(table_name, db.metadata, autoload_with=db.engine)

    # Retrieve the file path before deleting the row (specific to guidelines)
    file_path = None
    if table_name == 'guideline':
        guideline = db.session.query(table).filter_by(id=row_id).first()
        if guideline:
            file_path = guideline.file_path
            print(f"File path to delete: {file_path}")
        else:
            print(f"No guideline found with id: {row_id}")

    # Delete the row from the database
    stmt = table.delete().where(table.c.id == row_id)
    db.session.execute(stmt)
    db.session.commit()

    # Attempt to delete the file from the filesystem
    if file_path:
        # Adjust the path to correctly point to the actual file location
        full_file_path = os.path.join(os.getcwd(), 'app', file_path)
        print(f"Looking for file at: {full_file_path}")
        if os.path.exists(full_file_path):
            try:
                os.remove(full_file_path)
                flash(f'File {os.path.basename(file_path)} deleted successfully.', 'success')
                print(f"File {full_file_path} deleted successfully.")
            except Exception as e:
                flash(f'Error deleting file: {str(e)}', 'danger')
                print(f"Error deleting file: {full_file_path}. Reason: {str(e)}")
        else:
            flash(f'File {full_file_path} not found on the server.', 'warning')
            print(f"File {full_file_path} not found on the server.")
    else:
        flash('No file path available to delete.', 'warning')
        print("No file path available to delete.")

    flash(f'Row {row_id} deleted from {table_name}.', 'success')
    return redirect(url_for('main.view_table_data', table_name=table_name))
# *===================================================================
# Content Management Routes
# *===================================================================
# Admin- add gideline route
@bp.route('/admin/add_guideline', methods=['GET', 'POST'])
@login_required
def add_guideline():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main_routes.index'))

    form = AddGuidelineForm()

    if form.validate_on_submit():
        try:
            # Data dictionary to hold the form data
            data = {
                'title': form.title.data.strip(),
                'file_type': form.file_type.data,
                'file_path': None,  # Initialize file_path as None
                'url': form.url.data.strip() if form.url.data else None,
                'embed_code': form.embed_code.data.strip() if form.embed_code.data else None
            }

            # Handle file upload if present
            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename:
                    # Format the filename based on the title and file type
                    title = form.title.data.strip().lower().replace(' ', '_')
                    file_type = file.filename.split('.')[-1].lower()
                    filename = f"{title}.{file_type}"

                    # Correct directory path
                    folder_path = os.path.join('app', 'files', 'guideline')
                    os.makedirs(folder_path, exist_ok=True)

                    # Save the file to the correct location
                    file_path = os.path.join(folder_path, filename)
                    file.save(file_path)

                    # Store the file path and type in the data dictionary
                    data['file_path'] = file_path
                    data['file_type'] = file_type  # Update file_type with the actual file extension

            # Ensure that at least one content field is provided
            if not data['file_path'] and not data['url'] and not data['embed_code']:
                flash('Please provide at least one content type: a file upload, a URL, or an embed code.', 'warning')
                return redirect(url_for('main.add_guideline'))

            # Insert the new guideline into the database
            guideline = Guideline(**data)
            db.session.add(guideline)
            db.session.commit()

            flash('New guideline has been added successfully.', 'success')
            return redirect(url_for('app_admin.admin_dashboard'))

        except Exception as e:
            print(f"Error occurred: {str(e)}")
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('main.add_guideline'))

    return render_template('add_guideline.html', form=form)


# Admin- add curated content route
@bp.route('/admin/add_curated_contents', methods=['GET', 'POST'])
@login_required
def add_curated_contents():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main_routes.index'))

    if request.method == 'POST':
        # Add your curated content processing logic here
        flash('Curated content added successfully!', 'success')
        return redirect(url_for('app_admin.admin_dashboard'))

    return render_template('add_curated_contents.html')

#Admin- add radiology calcuator route
@bp.route('/admin/add_radiology_calculators', methods=['GET', 'POST'])
@login_required
def add_radiology_calculators():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main_routes.index'))

    if request.method == 'POST':
        # Add your radiology calculators processing logic here
        flash('Radiology calculator added successfully!', 'success')
        return redirect(url_for('app_admin.admin_dashboard'))

    return render_template('add_radiology_calculators.html')


# *----------------------------------------------------------------
# * Route for session-related information, audits, database updates, and logging.
# ----------------------------------------------------------------
@bp.route('/index/<string:category>/<int:content_id>', methods=['POST'])
def session_auditing(category, content_id):
    """
    This route handles access to content based on its category and ID.
    It increments the access_count each time the content is accessed,
    updates the view duration, logs session data into usage_statistics,
    and captures other interaction details into the UserContent model.
    """

    # Check if the user is authenticated
    if not current_user.is_authenticated:
        return jsonify({'error': 'User not authenticated'}), 403

    # Fetch start and end times from request data
    start_time = request.json.get('start_time')
    end_time = request.json.get('end_time')
    interaction_type = request.json.get('interaction_type', 'viewed')  # Default to 'viewed'
    content_rating = request.json.get('content_rating')  # Optional rating provided by user

    # Ensure start and end times are provided
    if not start_time or not end_time:
        bp.logger.error('Start time or end time missing in session auditing.')
        return jsonify({'error': 'Start time or end time missing'}), 400

    # Convert start and end times to datetime objects
    try:
        start_time = datetime.fromisoformat(start_time)
        end_time = datetime.fromisoformat(end_time)
    except ValueError as e:
        bp.logger.error(f'Error parsing datetime: {str(e)}')
        return jsonify({'error': 'Invalid date format'}), 400

    # Calculate view duration in seconds
    view_duration = int((end_time - start_time).total_seconds())

    # Fetch the content by ID and validate category
    content = db.session.query(Contents).filter_by(id=content_id, category=category).first()
    user_content = db.session.query(UserContent).filter_by(content_id=content_id, user_id=current_user.id).first()

    if content:
        # Increment the access_count
        content.access_count = (content.access_count or 0) + 1
        
        # Update view_duration by adding the new duration
        content.view_duration = (content.view_duration or 0) + view_duration
        
        # Update last_accessed timestamp
        content.last_accessed = datetime.now(timezone.utc)
        
        # Update bookmark count if the interaction type is 'bookmark'
        if interaction_type == 'bookmark':
            content.bookmark_count = (content.bookmark_count or 0) + 1

        # Prepare session data for logging and updating usage_statistics
        session_data = {
            'content_id': content.id,
            'title': content.title,
            'category': content.category,
            'access_count': content.access_count,
            'view_duration': content.view_duration,
            'last_accessed': content.last_accessed.isoformat(),
            'user_id': current_user.id,
            'email': current_user.email,
            'is_paid': current_user.is_paid,
            'interaction_type': interaction_type,
            'content_rating': content_rating
        }

        # Update usage_statistics with session data as JSON string
        content.usage_statistics = json.dumps(session_data)

        # Add or update interaction data in UserContent model
        if user_content:
            # Update existing interaction record
            user_content.interaction_type = interaction_type
            user_content.interaction_date = datetime.now(timezone.utc)
            user_content.content_rating = content_rating
            user_content.time_spent += view_duration
            user_content.last_interaction = datetime.now(timezone.utc)
        else:
            # Create new interaction record
            user_content_data = UserContent(
                user_id=current_user.id,
                content_id=content_id,
                interaction_type=interaction_type,
                interaction_date=datetime.now(timezone.utc),
                feedback=None,  # Assuming feedback is handled separately
                content_rating=content_rating,
                time_spent=view_duration,
                last_interaction=datetime.now(timezone.utc)
            )
            db.session.add(user_content_data)
        

        # Commit the changes to the database
        db.session.commit()
        
        # Log the successful access
        bp.logger.info(f"Content accessed successfully: {session_data}")

        return jsonify(session_data)
    
    # Handle case where content is not found
    bp.logger.error('Content not found during session auditing.')
    return jsonify({'error': 'Content not found'}), 404
# *----------------------------------------------------------------

# *===================================================================
# Content navigation and content serving routes
# *===================================================================
# *----------------------------------------------------------------
# ! home route moved to main.py

# *----------------------------------------------------------------
# Other Navigation Bar Routes
@bp.route('/pricing')
def pricing():
    return render_template('pricing.html')

@bp.route('/contact_us')
def contact_us():
    return render_template('contact_us.html')

@bp.route('/review_us')
def review_us():
    return render_template('review_us.html')


# ===================================================================
# Development and Debug Routes
# ===================================================================

# *----------------------------------------------------------------
# Debug Route
@bp.route('/debug')
def debug():
    return render_template('debug.html')

# *----------------------------------------------------------------
# Reset the Database (except users)
@bp.route('/reset_db')
@login_required
def reset_db():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main_routes.index'))

    guidelines_folder = os.path.join('files', 'guidelines')
    
    try:
        if os.path.exists(guidelines_folder):
            for filename in os.listdir(guidelines_folder):
                guideline_folder = os.path.join('app', 'files', 'guideline')
                os.makedirs(guideline_folder, exist_ok=True)
                file_path = os.path.join(guideline_folder, filename)
                
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
    except Exception as e:
        print(f'Failed to delete files in {guidelines_folder}. Reason: {e}')

    meta = db.metadata
    with db.engine.connect() as conn:
        for table in reversed(meta.sorted_tables):
            if table.name != 'users':  # Skip the Users table
                conn.execute(f'DROP TABLE IF EXISTS {table.name}')

    db.create_all()
    flash('Database reset successfully, users preserved.', 'success')
    return redirect(url_for('app_admin.admin_dashboard'))


#todo Routes for card items (in development mode)
@bp.route('/buy_now')
def buy_now():
    return render_template('buy_now.html')

@bp.route('/free_trial')
def free_trial():
    return render_template('free_trial.html')
@bp.route('/classifications')
@login_required
def classifications():
    return render_template('classifications.html')

@bp.route('/differential_diagnosis')
@login_required
def differential_diagnosis():
    return render_template('differential_diagnosis.html')

@bp.route('/vetting_tools')
@login_required
def vetting_tools():
    return render_template('vetting_tools.html')

@bp.route('/anatomy')
@login_required
def anatomy():
    return render_template('anatomy.html')

@bp.route('/curated_content')
@login_required
def curated_content():
    return render_template('curated_content.html')

@bp.route('/report_checker')
@login_required
def report_checker():
    return render_template('report_checker.html')

@bp.route('/rad_calculators')
@login_required
def rad_calculators():
    return render_template('rad_calculators.html')

@bp.route('/tnm_staging')
@login_required
def tnm_staging():
    return render_template('tnm_staging.html')

@bp.route('/image_search')
@login_required
def image_search():
    return render_template('image_search.html')

@bp.route('/physics')
@login_required
def physics():
    return render_template('physics.html')

@bp.route('/governance_audits')
@login_required
def governance_audits():
    return render_template('governance_audits.html')

@bp.route('/courses')
@login_required
def courses():
    return render_template('courses.html')

@bp.route('/research_tools')
@login_required
def research_tools():
    return render_template('research_tools.html')

@bp.route('/music')
@login_required
def music():
    return render_template('music.html')

#######################################################################