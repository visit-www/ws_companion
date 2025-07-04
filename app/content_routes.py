# * Imports
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify,send_from_directory
from flask_login import login_required, current_user
from .models import Content, Reference
from . import db
from sqlalchemy import or_ 
from .util import inline_references  # Import from utils

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
    # Retrieve references that match the category and module of the document
    references = db.session.query(Reference).filter(
        or_(Reference.category == document.category,
        Reference.module == document.module,
        Reference.content_id == document.id
        )
    ).all()
    # Generate file_url for easy passing to serve_file function
    file_url = url_for('content_routes.serve_file', filepath=document.filepath)
    file_name = f"Reading {document.title.capitalize()}" if document.title else "You are reading Document"
    file_path = os.path.join(basedir, document.filepath)
    # Check if the file is a report template (.docx)
    if category=='report_template'.upper():
        return render_template('smart_report_viewer.html',references=references)
    # Check if the file is a Mermaid diagram (.mmd)
    elif document.file.endswith('.mmd'):
        # Read the content of the Mermaid .mmd file
        print(f"debug 2 : figuring out file_url by calling serve_file route is {file_path}")
        with open(file_path, 'r') as file:
            diagram_content = file.read()
        # Render Mermaid diagram viewer
        return render_template('mermaid_viewer.html', doc=document, cat=category, display_name=display_name, diagram_content=diagram_content, references=references)
    # Handle SVG, PNG, and HTML files
    elif document.file.endswith(('.svg', '.png')):
        # Handle SVG, PNG, and HTML in drawio_viewer.html
        return render_template('drawio_viewer.html', doc=document, cat=category, display_name=display_name, file_url=file_url, references=references)
    elif document.file.endswith(('.html')):
    
        # Read the content of the HTML file
        with open(file_path, 'r') as file:
            html_content = file.read()
        # Handle HTML files in html_viewer.html
        processed_html_content = inline_references(html_content, references)
        return render_template('html_viewer.html', html_content=processed_html_content, doc=document, cat=category, display_name=display_name, references=references)
    else:
        # Render PDF viewer for unsupported files (default fallback)
        print(file_url)
        return render_template('pdf_viewer.html', doc=document, cat=category, display_name=display_name, file_url=file_url, file_name=file_name, references=references)
# Route to safely serve files to users in dcoument viewer
@content_routes_bp.route('/files/<path:filepath>')
@login_required
def serve_file(filepath):
    rel_path='/'.join(filepath.split('/')[1:])
    # Serve files from the UPLOAD_FOLDER
    served_path=os.path.join(upload_folder, rel_path)
    print(f"debugginh: I am showing yu the served path {served_path}")
    return send_from_directory(upload_folder, rel_path)
# Updated content_routes.py for reference page
@content_routes_bp.route('/references', methods=['GET', 'POST'])
@login_required
def reference_page():
    references = db.session.query(Reference).order_by(Reference.updated_at.desc()).all()
    display_name="References"
    
    # Use a dictionary to store content details
    content_dict = {}
    
    for content in references:
        keyword = content.category.value if content.category else None
        content_dict[content.id] = {'keyword': keyword}

    return render_template('reference.html',contents=references,content_dict=content_dict, display_name=display_name)

@content_routes_bp.route('/reference/<category>/<display_name>/<uuid:reference_id>', methods=['GET'])
@login_required
def view_reference(category, display_name, reference_id):
    referring_url = request.referrer or url_for('main_routes.index')


    # Fetch the reference by id
    reference = db.session.query(Reference).filter_by(id=reference_id).first()

    # Ensure the reference exists; redirect if not found
    if not reference:
        flash('Reference document not found', 'warning')
        return redirect(referring_url)

    # Retrieve references that match the category or module of the reference
    references = db.session.query(Reference).filter(
        or_(
            Reference.category == reference.category,
            Reference.module == reference.module
        )
    ).all()

    # Generate file URL for serving the file
    file_url = url_for('content_routes.serve_file', filepath=reference.filepath)
    file_name = f"Reading {reference.title.capitalize()}" if reference.title else "You are reading Reference Document"
    file_path = os.path.join(basedir, reference.filepath)

    # Determine the appropriate viewer based on file type
    if category.upper() == 'REPORT_TEMPLATE':
        return render_template('smart_report_viewer.html', doc=reference, references=references, display_name=display_name)

    elif reference.file.endswith('.mmd'):
        # Read and render Mermaid diagram
        with open(file_path, 'r') as file:
            diagram_content = file.read()
        return render_template('mermaid_viewer.html', doc=reference, display_name=display_name, diagram_content=diagram_content, references=references)

    elif reference.file.endswith(('.svg', '.png')):
        # Render SVG or PNG in drawio_viewer.html
        return render_template('drawio_viewer.html', doc=reference, display_name=display_name, file_url=file_url, references=references)

    elif reference.file.endswith('.html'):
        # Read and render HTML content
        with open(file_path, 'r') as file:
            html_content = file.read()
        processed_html_content = inline_references(html_content, references)
        return render_template('html_viewer.html', html_content=processed_html_content, doc=reference, display_name=display_name, references=references)

    else:
        # Default to PDF viewer
        return render_template('pdf_viewer.html', doc=reference, display_name=display_name, file_url=file_url, file_name=file_name, references=references)
