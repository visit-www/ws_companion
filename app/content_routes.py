# * Imports
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from .models import Content
from . import db
import os

# * Blueprint setup
content_routes_bp = Blueprint(
    'content_routes', __name__,
    static_folder='static',
    static_url_path='/static'
)

# Global Error Handling
#@content_routes_bp.errorhandler(Exception)
#def handle_exception(e):
#    content_routes_bp.logger.error(f"Unhandled Exception in Content Navigation Blueprint: {e}", exc_info=True)
#    return jsonify({'error': 'An internal error occurred'}), 500

# * Content navigation routes 
@content_routes_bp.route('/<category>', methods=['GET'])
@login_required
def view_category(category):
    # Fetch contents based on the category from the URL
    contents = db.session.query(Content).filter_by(category=category).all()
    
    # Ensure the template exists or provide a default fallback
    template_name = f"{category}.html"
    if not os.path.exists(os.path.join('app/templates', template_name)):
        flash(f"No page found for category {category}.", 'warning')
        return redirect(url_for('main_routes.index'))  # Redirect to index if the template is missing
    

    return render_template(template_name, contents=contents)