# * Imports
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify,send_from_directory
from flask_login import login_required, current_user
from .models import Content
from . import db
import os
from config import Config
upload_folder=Config.UPLOAD_FOLDER

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
def view_document(category, id):
    category=category.split('.')[-1]
    display_name=request.args.get('display_name')
    # Fetch the document from the database based on its ID
    document = db.session.query(Content).filter_by(id=id).first()
    # Ensure the document exists
    if not document:
        flash('Document not found', 'warning')
        return redirect(url_for('main_routes.index'))

    # Render the document_viewer.html template with the document data
    return render_template('document_viewer.html', doc=document, cat=category, display_name=display_name)

# Route to safely serve files to users in dcoument viewer
@content_routes_bp.route('/files/<path:filepath>')
@login_required
def serve_file(filepath):
    rel_path='/'.join(filepath.split('/')[1:])
    # Serve files from the UPLOAD_FOLDER
    served_path=os.path.join(upload_folder, rel_path)
    print(served_path)
    return send_from_directory(upload_folder, rel_path)