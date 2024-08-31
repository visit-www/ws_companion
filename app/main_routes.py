from flask import Blueprint, render_template,jsonify
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