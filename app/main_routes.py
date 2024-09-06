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
    cat_list = []

    # Loop through each enum member in the CategoryNames enum
    for enum_object in CategoryNames:
        # Split the enum member name by underscores into a list of words
        cat = enum_object.name.split("_")
        
        # Capitalize the first letter of each word and join them back into a string
        capit_cat = [word.capitalize() for word in cat]
        
        # Join the capitalized words with spaces to form a readable category name
        category = " ".join(capit_cat)
        
        # Add the formatted category name to the list
        cat_list.append(category)

    # Create a dictionary mapping each category name to its index
    cat_dict = {cat: idx for idx, cat in enumerate(cat_list)}

    # Render the 'index.html' template, passing the category dictionary to the template
    return render_template('index.html', cat_dict=cat_dict)
#!----------------------------------------------------------------
# jsonify data for react :
@main_bp.route('/api/data')
def react_index():
    # Initialize an empty list to hold the formatted category names
    cat_list = []

    # Loop through each enum member in the CategoryNames enum
    for enum_object in CategoryNames:
        # Split the enum member name by underscores into a list of words
        cat = enum_object.name.split("_")
        
        # Capitalize the first letter of each word and join them back into a string
        capit_cat = [word.capitalize() for word in cat]
        
        # Join the capitalized words with spaces to form a readable category name
        category = " ".join(capit_cat)
        
        # Add the formatted category name to the list
        cat_list.append(category)

    # Create a dictionary mapping each category name to its index
    cat_dict = {cat: idx for idx, cat in enumerate(cat_list)}

    # Render the 'index.html' template, passing the category dictionary to the template
    return jsonify(cat_dict)

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