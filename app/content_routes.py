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
    display_name=request.args.get('display_name')
    cat_contents= db.session.query(Content).filter_by(category=category).all()
    return render_template('category.html',contents=cat_contents, display_name=display_name)
@content_routes_bp.route('/<category>/<id>', methods=['GET'])
@login_required
def view_content(category, id):
    return("This is intended to be handled by React front end")