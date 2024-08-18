import os
import shutil
import webbrowser
import threading
import socket
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import inspect, Table

def get_local_ip():
    """Get the local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # This doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        ip_address = s.getsockname()[0]
    except Exception:
        ip_address = '127.0.0.1'
    finally:
        s.close()
    return ip_address

def open_browser():
    local_ip = get_local_ip()
    webbrowser.open_new(f"http://{local_ip}:5001")

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', "7ebfffbf75e406f1b63739a0c5e487496be74113d2fd3a672fc45b4a120f571b")

# Use PostgreSQL if the DATABASE_URL environment variable is set (as it would be on Heroku), otherwise default to SQLite
# Use PostgreSQL if the DATABASE_URL environment variable is set (as it would be on Heroku), otherwise default to SQLite
if 'DATABASE_URL' in os.environ:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "radiology.db")}'

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "radiology.db")}'

db = SQLAlchemy(app)

# Define the Guideline model
class Guideline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<Guideline {self.title}>'
    
    
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirect to login page if unauthorized
login_manager.login_message = 'Please login to access this page'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_paid = db.Column(db.Boolean, default=False)  # Indicates if the user is a paid member
    is_admin = db.Column(db.Boolean, default=False)  # Admin status

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Existing routes remain unchanged...

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        
        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'warning')
            return redirect(url_for('register'))
        
        if username and password:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, password=hashed_password, is_paid=False)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Both fields are required.', 'danger')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful! Welcome back.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login failed. Please check your username and password and try again.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template('index.html')

#add routes for admin access: we want to render admin dashboard to start with :
@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_guideline':
            # Implement logic for adding guidelines
            flash('Add Guidelines feature is under construction.', 'info')
            return redirect(url_for('add_guidelines'))

        elif action == 'add_curated_contents':
            # Implement logic for adding curated content
            flash('Add Curated Content feature is under construction.', 'info')
            return redirect(url_for('add_curated_contents'))

        elif action == 'add_radiology_calculators':
            # Implement logic for adding radiology calculators
            flash('Add Radiology Calculators feature is under construction.', 'info')
            return redirect(url_for('add_radiology_calculators'))

        elif action == 'user_management':
            # Redirect to user management page
            return redirect(url_for('user_management'))

        return redirect(url_for('admin_dashboard'))

    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

#Route for adding guidelines :
@app.route('/admin/add_guidelines', methods=['GET', 'POST'])
@login_required
def add_guidelines():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Add your guideline processing logic here
        flash('Guideline added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_guidelines.html')

# Route of adding curated contents :
@app.route('/admin/add_curated_contents', methods=['GET', 'POST'])
@login_required
def add_curated_contents():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Add your curated content processing logic here
        flash('Curated content added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_curated_contents.html')

# Route for adding radioloy calculators 
@app.route('/admin/add_radiology_calculators', methods=['GET', 'POST'])
@login_required
def add_radiology_calculators():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Add your radiology calculators processing logic here
        flash('Radiology calculator added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('add_radiology_calculators.html')

# Route for user management :
@app.route('/admin/user_management', methods=['GET', 'POST'])
@login_required
def user_management():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Add your user management logic here
        flash('User management action performed successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    users = User.query.all()
    return render_template('user_management.html', users=users)
# Rotue fo db managment (other reseting and db visualizing routes are in the end)
@app.route('/admin/db_management')
@login_required
def db_management():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))

    # Create the inspector object
    inspector = inspect(db.engine)  # Ensure `db.engine` is used here

    # Get a list of all table names
    tables = inspector.get_table_names()

    return render_template('db_management.html', tables=tables)


# Add routes for the new features based on navbar and cards

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/buy_now')
def buy_now():
    return render_template('buy_now.html')

@app.route('/free_trial')
def free_trial():
    return render_template('free_trial.html')

# View guidlines 
@app.route('/guidelines')
@login_required
def guidelines():
    # Fetch all guidelines from the database
    guidelines = Guideline.query.all()

    # Pass guidelines to the template for rendering
    return render_template('guidelines.html', guidelines=guidelines)

@app.route('/guideline/<int:id>')
@login_required
def serve_guideline(id):
    guideline = Guideline.query.get_or_404(id)
    file_name = os.path.basename(guideline.file_path)
    file_type = guideline.file_type.lower()
    
    # Determine the appropriate MIME type for serving the file
    mime_type = ''
    if file_type == 'pdf':
        mime_type = 'application/pdf'
    elif file_type in ['doc', 'docx']:
        mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif file_type == 'html':
        mime_type = 'text/html'
    elif file_type == 'xml':
        mime_type = 'application/xml'
    else:
        mime_type = 'application/octet-stream'  # Default for unknown types

    # Serve the file
    return send_from_directory(
        directory=os.path.dirname(guideline.file_path),
        path=file_name,
        mimetype=mime_type,
        as_attachment=False  # Serve inline instead of download
    )

@app.route('/classifications')
@login_required
def classifications():
    return render_template('classifications.html')

@app.route('/differential_diagnosis')
@login_required
def differential_diagnosis():
    return render_template('differential_diagnosis.html')

@app.route('/vetting_tools')
@login_required
def vetting_tools():
    return render_template('vetting_tools.html')

@app.route('/anatomy')
@login_required
def anatomy():
    return render_template('anatomy.html')

@app.route('/curated_content')
@login_required
def curated_content():
    return render_template('curated_content.html')

@app.route('/report_checker')
@login_required
def report_checker():
    return render_template('report_checker.html')

@app.route('/rad_calculators')
@login_required
def rad_calculators():
    return render_template('rad_calculators.html')

@app.route('/tnm_staging')
@login_required
def tnm_staging():
    return render_template('tnm_staging.html')

@app.route('/image_search')
@login_required
def image_search():
    return render_template('image_search.html')

@app.route('/physics')
@login_required
def physics():
    return render_template('physics.html')

@app.route('/governance_audits')
@login_required
def governance_audits():
    return render_template('governance_audits.html')

@app.route('/courses')
@login_required
def courses():
    return render_template('courses.html')

@app.route('/research_tools')
@login_required
def research_tools():
    return render_template('research_tools.html')

@app.route('/music')
@login_required
def music():
    return render_template('music.html')

@app.route('/contact_us')
def contact_us():
    return render_template('contact_us.html')

@app.route('/review_us')
def review_us():
    return render_template('review_us.html')

# Route to reset users
@app.route('/admin/reset_users')
@login_required
def reset_users():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))

    # Delete all users from the database
    User.query.delete()
    db.session.commit()
    flash('All users have been reset successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# Route to view database tables
@app.route('/admin/db_tables')
@login_required
def db_tables():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))

    # Create the inspector object
    inspector = inspect(db.engine)

    # Get a list of all table names
    tables = inspector.get_table_names()

    return render_template('db_tables.html', tables=tables)

@app.route('/admin/db_tables/view/<table_name>')
@login_required
def view_table_data(table_name):
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))

    # Reflect the table from the database
    table = db.Table(table_name, db.metadata, autoload_with=db.engine)

    # Fetch all data from the table
    query = db.session.query(table).all()

    # Pass both the rows, the table metadata, and getattr to the template
    return render_template('view_table_data.html', table_name=table_name, rows=query, table=table, getattr=getattr)

# functiosn to add and delte specfic data row from admin dashborad :
# Route to delete a row from a specific table
@app.route('/admin/db_tables/delete/<table_name>/<int:row_id>', methods=['POST'])
@login_required
def delete_row(table_name, row_id):
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))

    # Reflect the table from the database
    table = db.Table(table_name, db.metadata, autoload_with=db.engine)

    # Find and delete the row using filter_by
    stmt = table.delete().where(table.c.id == row_id)
    db.session.execute(stmt)
    db.session.commit()

    flash(f'Row {row_id} deleted from {table_name}.', 'success')
    return redirect(url_for('view_table_data', table_name=table_name))

    # Delete the row
    db.session.delete(row)
    db.session.commit()
    flash(f'Row {row_id} has been deleted from {table_name}.', 'success')
    return redirect(url_for('view_table_data', table_name=table_name))

# Route to add a new row to a specific table
@app.route('/admin/db_tables/add/<table_name>', methods=['GET', 'POST'])
@login_required
def add_row(table_name):
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))

    table = db.metadata.tables.get(table_name)
    if table is None:
        flash(f'Table {table_name} does not exist.', 'danger')
        return redirect(url_for('db_tables'))

    if request.method == 'POST':
        try:
            data = {}
            for column in table.columns:
                print(f"Processing column: {column.name}")
                if column.name != 'id':  # Skip 'id' column
                    if column.name == 'file_path':  # Handle file upload
                        if column.name in request.files:
                            file = request.files.get(column.name)
                            if file and file.filename:
                                # Format the file name based on the title and file type
                                title = request.form.get('title', '').strip().lower().replace(' ', '-')
                                file_type = request.form.get('file_type', '').strip().lower()
                                filename = f"{title}.{file_type}"

                                # Ensure the directory exists and save the file
                                folder_path = os.path.join('files', table_name)
                                os.makedirs(folder_path, exist_ok=True)
                                file_path = os.path.join(folder_path, filename)
                                file.save(file_path)

                                # Store the file path in the data to be inserted
                                data[column.name] = file_path
                            else:
                                flash(f'File not provided for {column.name}.', 'danger')
                                return redirect(url_for('add_row', table_name=table_name))
                        else:
                            flash(f'No file upload field named {column.name} in form.', 'danger')
                            return redirect(url_for('add_row', table_name=table_name))
                    else:
                        # Store the form data for other columns
                        data[column.name] = request.form.get(column.name, '').strip()

            print(f"Data to be inserted: {data}")

            # Insert the new row into the database
            insert_stmt = table.insert().values(**data)
            db.session.execute(insert_stmt)
            db.session.commit()

            flash(f'New {table_name[:-1]} has been added.', 'success')
            return redirect(url_for('view_table_data', table_name=table_name))

        except Exception as e:
            print(f"Error occurred: {str(e)}")
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('add_row', table_name=table_name))

    # Render a form to add a new row
    return render_template('add_row.html', table_name=table_name, columns=table.columns)



# Reset the database (exept users)
@app.route('/reset_db')
@login_required
def reset_db():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))

    # Delete all files in the guidelines directory
    folder = os.path.join(basedir, 'files/guidelines')
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

    # Drop specific tables (but not the User table)
    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        if table.name != 'user':  # Skip the User table
            db.engine.execute(f'DROP TABLE IF EXISTS {table.name}')

    # Recreate all tables
    db.create_all()

    flash('Database reset successfully, users preserved.', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    # Start a thread to open the browser after the Flask app starts
    threading.Timer(1, open_browser).start()
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)