from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import shutil
import webbrowser
import threading
import socket

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

# Existing routes remain unchanged...

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

@app.route('/guidelines')
@login_required
def guidelines():
    return render_template('guidelines.html')

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

# Reset the database
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

if __name__ == "__main__":
    # Start a thread to open the browser after the Flask app starts
    threading.Timer(1, open_browser).start()
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)