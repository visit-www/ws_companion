from flask import Blueprint, render_template,jsonify, request, flash, send_from_directory
from flask_wtf.csrf import generate_csrf
from .models import Content, User, AdminReportTemplate, ClassificationSystem, ImagingProtocol, db, CategoryNames, UserData, Reference, ModalityEnum, BodyPartEnum
from . import db
from flask_cors import CORS
from flask_login import current_user, AnonymousUserMixin, login_required
from config import userdir, creativesfolder

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
#commented out : temporary route ot test error handling
#@main_bp.route("/_force_error")
#def force_error():
    #1 / 0  # deliberate ZeroDivisionError return jsonify({'error': 'An internal error occurred'}), 500

#----------------------------------------------------------------
# Route for Home/Index Page
# Define a route for the index page of the main blueprint
@main_bp.route('/')
def index():
    # Check if the current user is authenticated (not anonymous)
    if current_user.is_authenticated:
        
        # Fetch the user data object
        user_data = db.session.query(UserData).filter_by(user_id=current_user.id).first()
        print(f"UserData: {user_data}\n User id: {current_user.id}")

        # Check if the user data exists and then access 'last_interaction'
        if user_data:
            last_login = user_data.last_login
        else:
            last_login = "Not available"  # Handle the case where user data is not found
    else:
        last_login = "Not available"  # Handle the case for anonymous users
    
    # Render the 'index.html' template, passing the category dictionary to the template
    return render_template('index.html',last_login=last_login)

# *---------------------------------------------------------------
# Radilogy tools routes.
@main_bp.route("/tools", methods=["GET"])
@login_required
def radiology_tools():
    """
    Landing page for Radiology Tools:
    - Report templates (AdminReportTemplate)
    - Staging / classification systems
    - Imaging protocols
    With optional filters: modality, body_part, query (free text).
    """

    # Read filters from query string
    modality_param = request.args.get("modality") or ""
    body_part_param = request.args.get("body_part") or ""
    query = request.args.get("q") or ""

    # Resolve enums from params (we'll use enum.name in the HTML)
    selected_modality = None
    selected_body_part = None

    if modality_param:
        try:
            selected_modality = ModalityEnum[modality_param]
        except KeyError:
            selected_modality = None

    if body_part_param:
        try:
            selected_body_part = BodyPartEnum[body_part_param]
        except KeyError:
            selected_body_part = None

    # Base queries
    tpl_q = db.session.query(AdminReportTemplate).filter(
        AdminReportTemplate.is_active.is_(True)
    )
    cls_q = db.session.query(ClassificationSystem).filter(
        ClassificationSystem.is_active.is_(True)
    )
    proto_q = db.session.query(ImagingProtocol).filter(
        ImagingProtocol.is_active.is_(True)
    )

    # Apply modality/body_part filters where applicable
    if selected_modality is not None:
        tpl_q = tpl_q.filter(AdminReportTemplate.modality == selected_modality)
        cls_q = cls_q.filter(ClassificationSystem.modality == selected_modality)
        proto_q = proto_q.filter(ImagingProtocol.modality == selected_modality)

    if selected_body_part is not None:
        tpl_q = tpl_q.filter(AdminReportTemplate.body_part == selected_body_part)
        cls_q = cls_q.filter(ClassificationSystem.body_part == selected_body_part)
        proto_q = proto_q.filter(ImagingProtocol.body_part == selected_body_part)

    # Simple free text search on name/title fields
    if query:
        like = f"%{query}%"
        tpl_q = tpl_q.filter(AdminReportTemplate.template_name.ilike(like))
        cls_q = cls_q.filter(ClassificationSystem.name.ilike(like))
        proto_q = proto_q.filter(ImagingProtocol.name.ilike(like))

    templates = tpl_q.order_by(
        AdminReportTemplate.modality,
        AdminReportTemplate.body_part,
        AdminReportTemplate.template_name,
    ).all()

    classifications = cls_q.order_by(
        ClassificationSystem.category,
        ClassificationSystem.name,
    ).all()

    protocols = proto_q.order_by(
        ImagingProtocol.modality,
        ImagingProtocol.body_part,
        ImagingProtocol.name,
    ).all()

    # Provide enums for dropdowns
    modality_choices = list(ModalityEnum)
    body_part_choices = list(BodyPartEnum)

    return render_template(
        "radiology_tools.html",
        templates=templates,
        classifications=classifications,
        protocols=protocols,
        modality_choices=modality_choices,
        body_part_choices=body_part_choices,
        selected_modality=selected_modality,
        selected_body_part=selected_body_part,
        query=query,
    )

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
# ----------------------------------------------------------------
# File-serving routes (user uploads & creatives)
# ----------------------------------------------------------------

@main_bp.route('/user_data/<path:filename>')
@login_required  # Remove this if you really want it public, but login is safer
def serve_user_data(filename):
    """
    Serve files from the per-user data directory.
    """
    return send_from_directory(userdir, filename)


@main_bp.route('/creatives_folder/<path:filename>')
@login_required  # Optional but recommended
def serve_creatives_folder(filename):
    """
    Serve files from the creatives folder.
    """
    return send_from_directory(creativesfolder, filename)
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

#!-------- Refactoring UI - New routes -------------------
#! --- preview routes ------ !#
# New landing page- App Dashboard preview route #
#---------------------------------------------------------
@main_bp.route("/dashboard_preview")
def dashboard_preview():
    return render_template("app_dashboard.html")


#route to serve url for preview folder:
from flask import Blueprint, render_template, request, current_app, send_file, abort
import os
@main_bp.route('/preview/<filename>')
def static_preview(filename):
    # Go up one level from /app/ to project root
    preview_folder = os.path.abspath(os.path.join(current_app.root_path, '..', 'user_data', 'preview_reports'))
    file_path = os.path.join(preview_folder, filename)

    print(f"💡 Trying to serve: {file_path}")
    if not os.path.exists(file_path):
        print("❌ File not found!")
        return abort(404)

    try:
        return send_file(file_path, as_attachment=False)
    except Exception as e:
        print(f"❌ Error sending file: {e}")
        return abort(403)
