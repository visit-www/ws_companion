from flask import Blueprint, render_template,jsonify, request, flash
from flask_wtf.csrf import generate_csrf
from flask import render_template
from .models import CategoryNames,User,UserData,Reference
from . import db
from flask_cors import CORS
from flask_login import current_user, AnonymousUserMixin

#----------------------------------------------------------------
# Blueprint configuration
main_bp = Blueprint(
    'main_routes', __name__,
    static_folder='static',
    static_url_path='/static'
)
CORS(main_bp)

# *----------------------------------------------------------------
# todo: Global Error Handling Setup
# *----------------------------------------------------------------
#@main_bp.errorhandler(Exception)
#def handle_exception(e):
#    """Log exceptions specifically within the blueprint."""
#    main_bp.logger.error(f"Unhandled Exception in Blueprint: {e}", exc_info=True)
#    return jsonify({'error': 'An internal error occurred'}), 500

#----------------------------------------------------------------
# Route for Home/Index Page
# Define a route for the index page of the main blueprint
@main_bp.route('/')
def index():
    # Check if the current user is authenticated (not anonymous)
    if current_user.is_authenticated:
        
        # Fetch the user data object
        user_data = db.session.query(UserData).filter_by(user_id=current_user.id).first()
        print(f"UserData: {user_data}\n User id: {current_user.id}")

        # Check if the user data exists and then access 'last_interaction'
        if user_data:
            last_login = user_data.last_login
        else:
            last_login = "Not available"  # Handle the case where user data is not found
    else:
        last_login = "Not available"  # Handle the case for anonymous users
    
    # Render the 'index.html' template, passing the category dictionary to the template
    return render_template('index.html',last_login=last_login)
#!----------------------------------------------------------------
# Place holder routes for maain page navigations :

@main_bp.route('/pricing')
def pricing():
    return render_template('pricing.html')  # Placeholder HTML for "Pricing" page

@main_bp.route('/buy')
def buy_now():
    return render_template('buy_now.html')  # Placeholder HTML for "Buy NOw" page

@main_bp.route('/free-trial')
def free_trial():
    return render_template('free_trial.html')  # Placeholder HTML for "Free Trial" page

@main_bp.route('/contact-us')
def contact_us():
    return render_template('contact_us.html')  # Placeholder HTML for "Contact Us" page

@main_bp.route('/faq')
def faq():
    return render_template('faq.html')  # Placeholder HTML for "About Us" page

@main_bp.route('/review-us')
def review_us():
    return render_template('review_us.html')  # Placeholder HTML for "Review Us" page
# *----------------------------------------------------------------
#!Debugging routes:
@main_bp.route('/debug')
def debug():
    message=("The function failed- Thats why you are seeing this page!") 
    print(f"----------------------------\n{message}\n----------------------------")
    # Dynamically fetch the current route's name
    current_route = request.endpoint
    return render_template('test_routes.html',route=current_route, message=message)
#!------------------------------------------------------------------------

#!-------- Refactoring UI - New routes -------------------
#! --- preview routes ------ !#
# New landing page- App Dashboard preview route #
#---------------------------------------------------------
@main_bp.route("/dashboard_preview")
def dashboard_preview():
    return render_template("app_dashboard.html")
