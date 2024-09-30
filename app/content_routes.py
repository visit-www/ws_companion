# * Imports
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify,send_from_directory
from flask_login import login_required, current_user
from .models import Content
from . import db
import os
from config import Config,basedir
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
import ast
@content_routes_bp.route('/<category>', methods=['GET'])
@login_required
def view_category(category):
    # Fetch contents based on the category from the URL
    display_name = request.args.get('display_name')
    cat_contents = db.session.query(Content).filter_by(category=category).all()

    # Use a dictionary to store content details
    content_dict = {}
    
    for content in cat_contents:
        # Assuming keywords is a string of comma-separated values
        keyword = content.keywords.split(',')[0].strip().lower() if content.keywords else None
        print(f"debug: {content.keywords}")
        # Use ast.literal_eval to safely evaluate the list string
        try:
            accessibility_features = ast.literal_eval(content.accessibility_features) if content.accessibility_features else []
        except (ValueError, SyntaxError):
            accessibility_features = []  # Default to an empty list if parsing fails
        
        # Extract the first accessibility feature if available
        alt_text = accessibility_features[0] if accessibility_features else None
        # Add the content details to the dictionary
        content_dict[content.id] = {'keyword': keyword, 'alt_text': alt_text}
    print(f"debug: {content_dict}")
    return render_template('category.html', contents=cat_contents, content_dict=content_dict, display_name=display_name)
@content_routes_bp.route('/<category>/<id>', methods=['GET'])
@login_required
def view_document(category, id):
    category = category.split('.')[-1]
    display_name = request.args.get('display_name')

    # Fetch the document from the database based on its ID
    document = db.session.query(Content).filter_by(id=id).first()

    # Ensure the document exists
    if not document:
        flash('Document not found', 'warning')
        return redirect(url_for('main_routes.index'))

    # Generate file_url for easy passing to serve_file function
    file_url = url_for('content_routes.serve_file', filepath=document.filepath)
    file_name = f"Reading {document.title.capitalize()}" if document.title else "You are reading Document"
    
    # Check if the file is a Mermaid diagram (.mmd)
    if document.file.endswith('.mmd'):
        # Read the content of the Mermaid .mmd file
        mermaid_file_path = os.path.join(basedir, document.filepath)
        print(f"debug 2 : figuring out file_url by calling serve_file route is {mermaid_file_path}")
        with open(mermaid_file_path, 'r') as file:
            diagram_content = file.read()

        # Render Mermaid diagram viewer
        return render_template('mermaid_viewer.html', doc=document, cat=category, display_name=display_name, diagram_content=diagram_content)

    # Handle SVG, PNG, and HTML files
    elif document.file.endswith(('.svg', '.png', '.html')):
        # Handle SVG, PNG, and HTML in drawio_viewer.html
        return render_template('drawio_viewer.html', doc=document, cat=category, display_name=display_name, file_url=file_url)

    else:
        # Render PDF viewer for unsupported files (default fallback)
        print(file_url)
        return render_template('pdf_viewer.html', doc=document, cat=category, display_name=display_name, file_url=file_url, file_name=file_name)

# Route to safely serve files to users in dcoument viewer
@content_routes_bp.route('/files/<path:filepath>')
@login_required
def serve_file(filepath):
    rel_path='/'.join(filepath.split('/')[1:])
    # Serve files from the UPLOAD_FOLDER
    served_path=os.path.join(upload_folder, rel_path)
    print(f"debugginh: I am showing yu the served path {served_path}")
    return send_from_directory(upload_folder, rel_path)