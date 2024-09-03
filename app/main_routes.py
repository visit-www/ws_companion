from flask import Blueprint, render_template,jsonify, request
from flask_wtf.csrf import generate_csrf
from flask import render_template
#----------------------------------------------------------------
# Blueprint configuration
main_bp = Blueprint(
    'main_routes', __name__,
    static_folder='static',
    static_url_path='/static'
)

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
@main_bp.route('/')
def index():
    return render_template('index.html')
#!----------------------------------------------------------------
#!Debugging routes:
@main_bp.route('/debug')
def debug():
    message=("The function failed- Thats why you are seeing this page!") 
    print(f"----------------------------\n{message}\n----------------------------")
    # Dynamically fetch the current route's name
    current_route = request.endpoint
    return render_template('test_routes.html',route=current_route, message=message)
#!------------------------------------------------------------------------