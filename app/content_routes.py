# * Imports
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify,send_from_directory,abort
from flask_login import login_required, current_user
from . import db
from sqlalchemy import or_ 
from .util import inline_references  # Import from utils
import os
from config import Config,basedir
from werkzeug.utils import safe_join
from .models import (
    Content,
    Reference,
    AdminReportTemplate,
    ClassificationSystem,
    ImagingProtocol,
    )
from . import db
upload_folder=Config.UPLOAD_FOLDER
# *-------------------------------------------------------------------------
# * Blueprint setup
content_routes_bp = Blueprint(
    'content_routes', __name__,
    static_folder='static',
    static_url_path='/static'
)
# *-------------------------------------------------------------------------
# Helper: detect if client wants JSON (for API-style responses)
def wants_json_response() -> bool:
    """
    Decide if the client is explicitly asking for JSON.
    You can extend this later, for now we support:
    - Accept: application/json
    - ?format=json
    """
    if request.args.get("format") == "json":
        return True

    accept = request.headers.get("Accept", "")
    if "application/json" in accept.lower():
        return True
    return False

# -------------------------------------------------------------------------
# Helper: resolve an AdminReportTemplate filepath safely inside UPLOAD_FOLDER
# -------------------------------------------------------------------------
ALLOWED_TEMPLATE_EXTENSIONS = {".pdf", ".html", ".htm"}


def _resolve_template_file_path(filepath: str) -> tuple[str, str]:
    """
    Given a filepath stored in the DB (typically starting with 'files/...'),
    resolve it to a safe absolute path inside Config.UPLOAD_FOLDER.

    Returns (directory, filename) suitable for send_from_directory.
    Raises 404 if anything looks unsafe or missing.
    """
    if not filepath:
        abort(404)

    # Typical pattern in your app: 'files/some_subfolder/file.pdf'
    # Strip the leading 'files/' if present to get a relative path
    if filepath.startswith("files/"):
        rel_path = filepath[len("files/") :]
    else:
        # Assume it's already relative under UPLOAD_FOLDER
        rel_path = filepath.lstrip("/")

    # Use safe_join to avoid path traversal
    safe_path = safe_join(upload_folder, rel_path)
    if not safe_path:
        abort(404)

    # Normalise and ensure it is still under upload_folder
    safe_path = os.path.normpath(safe_path)
    if not safe_path.startswith(os.path.normpath(upload_folder)):
        abort(404)

    # Check extension – only allow PDF / HTML etc.
    _, ext = os.path.splitext(safe_path)
    if ext.lower() not in ALLOWED_TEMPLATE_EXTENSIONS:
        # You can use 403 to indicate "not allowed"
        abort(403)

    if not os.path.isfile(safe_path):
        abort(404)

    directory, filename = os.path.split(safe_path)
    return directory, filename

# *-------------------------------------------------------------------------

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

@content_routes_bp.route('/pdf_viewer')
def pdf_viewer():
    file_url = request.args.get('file_url')
    filename = request.args.get('filename')
    back_url = request.args.get('back_url', url_for('app_user.smart_report_dashboard'))  # Fallback to smart report dashboard

    return render_template('pdf_viewer.html', file_url=file_url, file_name=filename, back_url=back_url)

# *-------------------------------------------------------------------------
# Templates – list & detail
# -------------------------------------------------------------------------

@content_routes_bp.route("/templates", methods=["GET"])
@login_required
def list_templates():
    """
    List available reporting templates (AdminReportTemplate).
    Later we can add filters like modality=CT, body_part=BRAIN, etc.
    """
    # Optional filters
    modality = request.args.get("modality")
    body_part = request.args.get("body_part")
    search = request.args.get("q")

    query = db.session.query(AdminReportTemplate).filter_by(is_active=True)

    if modality:
        query = query.filter(AdminReportTemplate.modality == modality)

    if body_part:
        query = query.filter(AdminReportTemplate.body_part == body_part)

    if search:
        like = f"%{search}%"
        query = query.filter(
            AdminReportTemplate.template_name.ilike(like)
            | AdminReportTemplate.description.ilike(like)
            | AdminReportTemplate.tags.ilike(like)
        )

    templates = query.order_by(
        AdminReportTemplate.modality,
        AdminReportTemplate.body_part,
        AdminReportTemplate.template_name,
    ).all()

    if wants_json_response():
        # Return JSON representation
        data = []
        for t in templates:
            file_url = url_for(
            "content_routes.serve_template_file",
            template_id=t.id,
            _external=False,
            )
            data.append(
                {
                    "id": t.id,
                    "name": t.template_name,
                    "description": t.description,
                    "modality": t.modality.value if t.modality else None,
                    "body_part": t.body_part.value if t.body_part else None,
                    "category": t.category,
                    "module": t.module.value if t.module else None,
                    "tags": t.tags,
                    "template_type": t.template_type.value if hasattr(t, "template_type") and t.template_type else None,
                    "is_active": t.is_active,
                    "file_url": file_url,
                }
            )
        return jsonify({"templates": data})

    # HTML view – use a simple template for now (we can design it later)
    return render_template("templates/templates_list.html", templates=templates)

# *-------------------------------------------------------------------------
#Template detail: GET /content/templates/<id>
# -------------------------------------------------------------------------

@content_routes_bp.route("/templates/<int:template_id>", methods=["GET"])
@login_required
def get_template(template_id: int):
    """
    Get a single template (metadata + basic file info).
    Later, we can add logic to load the actual file content if needed.
    """
    template = db.session.query(AdminReportTemplate).filter_by(id=template_id).first()
    if template is None:
        abort(404)

    if wants_json_response():
        data = {
            "id": template.id,
            "name": template.template_name,
            "description": template.description,
            "modality": template.modality.value if template.modality else None,
            "body_part": template.body_part.value if template.body_part else None,
            "category": template.category,
            "module": template.module.value if template.module else None,
            "tags": template.tags,
            "template_type": template.template_type.value if hasattr(template, "template_type") and template.template_type else None,
            "is_active": template.is_active,
            "file": template.file,
            "filepath": template.filepath,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None,
            "file_url": url_for("content_routes.serve_template_file", template_id=template.id),
        }
        return jsonify(data)

    # HTML render – for now, reuse generic viewer later or make a specific page
    return render_template("templates/template_detail.html", template=template)
# *-------------------------------------------------------------------------
# Staging & classification systems – list
# -------------------------------------------------------------------------

@content_routes_bp.route("/staging", methods=["GET"])
@login_required
def list_classification_systems():
    """
    List available staging / classification systems (ClassificationSystem).
    Supports basic filtering by category, modality, body_part.
    """
    category = request.args.get("category")   # e.g., 'tnm', 'rads'
    modality = request.args.get("modality")
    body_part = request.args.get("body_part")
    search = request.args.get("q")

    query = db.session.query(ClassificationSystem).filter_by(is_active=True)

    if category:
        query = query.filter(ClassificationSystem.category == category)

    if modality:
        query = query.filter(ClassificationSystem.modality == modality)

    if body_part:
        query = query.filter(ClassificationSystem.body_part == body_part)

    if search:
        like = f"%{search}%"
        query = query.filter(
            ClassificationSystem.name.ilike(like)
            | ClassificationSystem.short_code.ilike(like)
            | ClassificationSystem.description.ilike(like)
        )

    systems = query.order_by(
        ClassificationSystem.category,
        ClassificationSystem.name,
    ).all()

    if wants_json_response():
        data = []
        for s in systems:
            data.append(
                {
                    "id": s.id,
                    "name": s.name,
                    "short_code": s.short_code,
                    "category": s.category.value if s.category else None,
                    "modality": s.modality.value if s.modality else None,
                    "body_part": s.body_part.value if s.body_part else None,
                    "version": s.version,
                    "description": s.description,
                    "is_active": s.is_active,
                    "definition": s.definition_json,
                }
            )
        return jsonify({"classifications": data})

    return render_template("staging/staging_list.html", systems=systems)

# -------------------------------------------------------------------------
# Imaging protocols – list
# -------------------------------------------------------------------------

@content_routes_bp.route("/protocols", methods=["GET"])
@login_required
def list_protocols():
    """
    List imaging protocols (ImagingProtocol).
    Basic filters: modality, body_part, emergency-only.
    """
    modality = request.args.get("modality")
    body_part = request.args.get("body_part")
    emergency_only = request.args.get("emergency")  # '1' or 'true' to filter
    search = request.args.get("q")

    query = db.session.query(ImagingProtocol).filter_by(is_active=True)

    if modality:
        query = query.filter(ImagingProtocol.modality == modality)

    if body_part:
        query = query.filter(ImagingProtocol.body_part == body_part)

    if emergency_only in ("1", "true", "True"):
        query = query.filter(ImagingProtocol.is_emergency.is_(True))

    if search:
        like = f"%{search}%"
        query = query.filter(
            ImagingProtocol.name.ilike(like)
            | ImagingProtocol.indication.ilike(like)
            | ImagingProtocol.tags.ilike(like)
        )

    protocols = query.order_by(
        ImagingProtocol.modality,
        ImagingProtocol.body_part,
        ImagingProtocol.name,
    ).all()

    if wants_json_response():
        data = []
        for p in protocols:
            data.append(
                {
                    "id": p.id,
                    "name": p.name,
                    "modality": p.modality.value if p.modality else None,
                    "body_part": p.body_part.value if p.body_part else None,
                    "indication": p.indication,
                    "is_emergency": p.is_emergency,
                    "uses_contrast": p.uses_contrast,
                    "contrast_details": p.contrast_details,
                    "technique_text": p.technique_text,
                    "parameters": p.parameters_json,
                    "tags": p.tags,
                    "is_active": p.is_active,
                }
            )
        return jsonify({"protocols": data})

    return render_template("protocols/protocols_list.html", protocols=protocols)

# -------------------------------------------------------------------------
# Secure file serving for template files
# -------------------------------------------------------------------------

@content_routes_bp.route("/templates/<int:template_id>/file", methods=["GET"])
@login_required
def serve_template_file(template_id: int):
    """
    Serve the underlying PDF/HTML file associated with an AdminReportTemplate.

    URL: /content/templates/<id>/file
    """
    template = db.session.query(AdminReportTemplate).filter_by(id=template_id, is_active=True).first()
    if template is None:
        abort(404)

    if not template.filepath:
        abort(404)

    directory, filename = _resolve_template_file_path(template.filepath)
    # We serve from the resolved directory, not always from UPLOAD_FOLDER root,
    # in case you organise templates in subfolders.
    return send_from_directory(directory, filename)

