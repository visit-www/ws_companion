from flask import Blueprint, render_template,jsonify, request, flash
from flask_wtf.csrf import generate_csrf
from flask import render_template
from .models import CategoryNames
from . import db
from flask_cors import CORS
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
    # Initialize an empty list to hold the formatted category names
    cat_dict = {}
    idx=-1

    # Loop through each enum member in the CategoryNames enum
    for enum_object in CategoryNames:
        # Split the enum member name by underscores into a list of words
        cat = enum_object.name.split("_")
        # Keep the enum_object to be passed to view_category route later. The categpres are being stores as enum object name (all caps)
        # we will need this later while seraching contents in a given category in view_category route. 
        cat_name=enum_object.name
    
        # Capitalize the first letter of each word and join them back into a string
        capit_cat = [word.capitalize() for word in cat]
        
        # Join the capitalized words with spaces to form a readable category name
        display_name = " ".join(capit_cat)
        idx+=1  # We need idx for given class name (class-idx) that is used by css to give card some colours.
        
        # Add the formatted category name to the list
        cat_dict[cat_name]=[display_name,idx]
    # Render the 'index.html' template, passing the category dictionary to the template
    return render_template('index.html', cat_dict=cat_dict)
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