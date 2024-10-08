from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User
from . import db
from .forms import AddGuidelineForm, AddUserForm
from .models import Guideline  # Ensure this is imported
import os
from flask import Blueprint, render_template, send_from_directory, request, redirect, url_for, flash
from sqlalchemy import inspect
from sqlalchemy import Table
import sqlalchemy as sa
import shutil

# Create the Blueprint instance
bp = Blueprint(
    'main', __name__,
    static_folder='static',  # Path to the static folder
    static_url_path='/static'  # URL to serve static files
)
#User authentication routes
@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        # Check if the username already exists
        existing_user = db.session.query(User).filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'warning')
            return redirect(url_for('main.register'))
        
        if username and password:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, password=hashed_password, is_paid=False)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('main.login'))
        else:
            flash('Both fields are required.', 'danger')
    
    return render_template('register.html')

# Log in route
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        # Query the user using SQLAlchemy's session
        user = db.session.query(User).filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Login successful! Welcome back.', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Login failed. Please check your username and password and try again.', 'danger')

    return render_template('login.html')

#Logout route
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))




# Admin Dashboard Route
@bp.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_guideline':
            return redirect(url_for('main.add_guideline'))

        elif action == 'add_curated_contents':
            flash('Add Curated Content feature is under construction.', 'info')
            return redirect(url_for('main.add_curated_contents'))

        elif action == 'add_radiology_calculators':
            flash('Add Radiology Calculators feature is under construction.', 'info')
            return redirect(url_for('main.add_radiology_calculators'))

        elif action == 'user_management':
            return redirect(url_for('main.db_tables.html'))

        return redirect(url_for('main.admin_dashboard'))

    users = db.session.query(User).all()
    return render_template('admin_dashboard.html', users=users)

# Add user route
@bp.route('/admin/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main.index'))

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
            return redirect(url_for('main.admin_dashboard'))  # Redirect to admin dashboard or another page
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('main.add_user'))

    return render_template('add_users.html', form=form)


# Admin- add gideline route
@bp.route('/admin/add_guideline', methods=['GET', 'POST'])
@login_required
def add_guideline():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main.index'))

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
            return redirect(url_for('main.admin_dashboard'))

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
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # Add your curated content processing logic here
        flash('Curated content added successfully!', 'success')
        return redirect(url_for('main.admin_dashboard'))

    return render_template('add_curated_contents.html')

#Admin- add radiology calcuator route
@bp.route('/admin/add_radiology_calculators', methods=['GET', 'POST'])
@login_required
def add_radiology_calculators():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # Add your radiology calculators processing logic here
        flash('Radiology calculator added successfully!', 'success')
        return redirect(url_for('main.admin_dashboard'))

    return render_template('add_radiology_calculators.html')


# Route for renddering Database Management page
@bp.route('/admin/db_management')
@login_required
def db_management():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main.index'))

    # Create the inspector object
    inspector = inspect(db.engine)

    # Get a list of all table names
    tables = inspector.get_table_names()

    return render_template('db_management.html', tables=tables)

################################
# * Route for serving guidlines

# Route for rendering the guidelines page, which shows all guidelines.
@bp.route('/guidelines')
@login_required
def guidelines():
    # Fetch all guidelines from the database
    guidelines = db.session.query(Guideline).all()
    
    # Extract file type and determine content type for each guideline
    guidelines_with_types = []
    for guideline in guidelines:
        if guideline.file_path:
            file_name = os.path.basename(guideline.file_path)
            file_type = file_name.split('.')[-1].lower()
        else:
            file_type = None  # No file available for this guideline

        # Determine content type
        content_type = None
        embed_code = None
        if guideline.embed_code:
            embed_code = guideline.embed_code
            if '<iframe' in guideline.embed_code:
                if 'youtube.com' in guideline.embed_code or 'vimeo.com' in guideline.embed_code:
                    content_type = 'video'
                else:
                    content_type = 'webpage'
            elif '<img' in guideline.embed_code:
                content_type = 'image'
            elif '</script>' in guideline.embed_code:
                content_type = 'script'
            else:
                content_type = 'unknown'  # For any other type of embed code
        
        card_id=str(guideline.id)
        card_index=f"card{card_id}"
        print(card_index)
        

        guidelines_with_types.append({
            'guideline': guideline,
            'file_type': file_type,
            'content_type': content_type,
            'embed_code': embed_code,
            'card_index':card_index,
        })
    
    # Pass guidelines with their file types and content types to the template for rendering
    return render_template('guidelines.html', guidelines_with_types=guidelines_with_types)

# Route for function that serves specific guideline files. 
@bp.route('/guideline/<int:id>')
@login_required
def serve_guideline(id):
    # Fetch the specific guideline by ID
    guideline = db.session.query(Guideline).filter(Guideline.id == id).first()
    
    if guideline.file_path:
        # Extract the file name and determine the file type
        file_name = os.path.basename(guideline.file_path)
        file_type = file_name.split('.')[-1].lower()
    
        # Define the MIME types for the files
        mime_type = {
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'html': 'text/html',
            'xml': 'application/xml'
        }.get(file_type, 'application/octet-stream')
    
        # Determine the absolute directory path
        full_directory = os.path.abspath(os.path.dirname(guideline.file_path))
    
        # Serve the file
        return send_from_directory(
        directory=full_directory,
        path=file_name,
        mimetype=mime_type,
        as_attachment=False  # Serve inline instead of downloading
        )
    else:
        flash('No file available for this guideline.', 'warning')
        return redirect(url_for('main.guidelines'))
########################################################################
#Route for nav bar

# Route for home/ Index page
@bp.route('/')
def index():
    return render_template('index.html')

#Other nav bar routes
@bp.route('/pricing')
def pricing():
    return render_template('pricing.html')


########################################################################
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

@bp.route('/contact_us')
def contact_us():
    return render_template('contact_us.html')

@bp.route('/review_us')
def review_us():
    return render_template('review_us.html')

########################################################################
#Datbase management routes

# Route to view all database tables
@bp.route('/admin/db_tables')
@login_required
def db_tables():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main.index'))

    # Create the inspector object
    inspector = inspect(db.engine)

    # Get a list of all table names
    tables = inspector.get_table_names()

    return render_template('db_tables.html', tables=tables)

# * Route of view specific table data
@bp.route('/admin/db_tables/view/<table_name>')
@login_required
def view_table_data(table_name):
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main.index'))

    # Reflect the table from the database
    table = Table(table_name, db.metadata, autoload_with=db.engine)

    # Fetch all data from the table
    query = db.session.query(table).all()

    # Pass both the rows, the table metadata, and getattr to the template
    return render_template('view_table_data.html', table_name=table_name, rows=query, table=table, getattr=getattr)


# >> Route to reset users
@bp.route('/admin/reset_users')
@login_required
def reset_users():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main.index'))

    # Delete all users from the database
    db.session.query(User).delete()
    db.session.commit()
    flash('All users have been reset successfully!', 'success')
    return redirect(url_for('main.admin_dashboard'))


# Route to delete a row from a specific table
@bp.route('/admin/db_tables/delete/<table_name>/<int:row_id>', methods=['POST'])
@login_required
def delete_row(table_name, row_id):
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main.index'))

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
################################
# ! Debuging routes
@bp.route('/debug')
def debug():
    return render_template('debug.html')

################################################################
# ! Debug: Route for Reset the database (except users)
################################################################
@bp.route('/reset_db')
@login_required
def reset_db():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main.index'))

    # Define the guidelines directory path
    guidelines_folder = os.path.join('files', 'guidelines')
    
    # Safely delete all files and subdirectories in the guidelines directory
    try:
        if os.path.exists(guidelines_folder):
            for filename in os.listdir(guidelines_folder):
                # Assuming 'filename' is the name of the file being uploaded
                guideline_folder = os.path.join('app', 'files', 'guideline')# Ensure the directory exists
                os.makedirs(guideline_folder, exist_ok=True)
                # Correct the file path
                file_path = os.path.join(guideline_folder, filename)
                
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
    except Exception as e:
        print(f'Failed to delete files in {guidelines_folder}. Reason: {e}')

    # Drop specific tables (except the User table)
    meta = db.metadata
    with db.engine.connect() as conn:
        for table in reversed(meta.sorted_tables):
            if table.name != 'user':  # Skip the User table
                conn.execute(f'DROP TABLE IF EXISTS {table.name}')

    #! Recreate all tables
    db.create_all()
    flash('Database reset successfully, users preserved.', 'success')
    return redirect(url_for('main.admin_dashboard'))