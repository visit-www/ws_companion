from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import shutil

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY',"7ebfffbf75e406f1b63739a0c5e487496be74113d2fd3a672fc45b4a120f571b")
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "radiology.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        new_user = User(username=username, password=hashed_password, is_paid=False)  # Default is unpaid
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login failed. Check your username and password.', 'danger')
    
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

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))

    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)

@app.route('/admin/update_paid_status/<int:user_id>')
@login_required
def update_paid_status(user_id):
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)
    user.is_paid = not user.is_paid
    db.session.commit()
    flash(f"Updated paid status for {user.username}.", 'success')
    return redirect(url_for('admin_dashboard'))

class Guideline(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<Guideline {self.title}>'

@app.route('/add_guidelines', methods=['GET', 'POST'])
@login_required
def add_guidelines():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form['title'].strip().title()
        file_type = request.form['file_type'].lower()
        file = request.files['file']

        if file:
            # Secure the filename and save the file
            filename = file.filename  # Use the original filename
            file_path_input = os.path.join('files/guidelines', filename)
            file.save(file_path_input)

            # Check for duplicate title or file path
            existing_guideline = Guideline.query.filter_by(title=title).first()
            if existing_guideline:
                return "Error: A guideline with this title already exists.", 400

            # Add the new guideline to the database
            new_guideline = Guideline(
                title=title,
                file_type=file_type,
                file_path=file_path_input
            )
            db.session.add(new_guideline)
            db.session.commit()

            print(f"Added guideline: {new_guideline.title}, Path: {new_guideline.file_path}")

            # Redirect to the success page
            return render_template('guideline_add_success.html', title=title)

    return render_template('add_guideline.html')

@app.route('/guideline/<int:id>')
def serve_guideline(id):
    guideline = Guideline.query.get_or_404(id)
    file_name = guideline.file_path.split('/')[-1]
    file_path = os.path.join('files/guidelines', file_name)
    try:
        return send_from_directory(directory='files/guidelines', path=file_name)
    except FileNotFoundError:
        flash('File not found.', 'danger')
        return redirect(url_for('index'))

@app.route('/guidelines')
def list_guidelines():
    guidelines = Guideline.query.all()  # Retrieve all guidelines from the database
    return render_template('guidelines_list.html', guidelines=guidelines)

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
    
    # Reset the database
    db.drop_all()
    db.create_all()
    flash('Database reset successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)