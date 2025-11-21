from flask import Blueprint, render_template, jsonify, request, flash, send_from_directory, redirect, url_for
from flask_wtf.csrf import generate_csrf
from .models import (
    Content,
    User,
    AdminReportTemplate,
    UserReportTemplate,
    ClassificationSystem,
    CategoryNames,
    UserData,
    Reference,
    ModalityEnum,
    BodyPartEnum,
    ImagingProtocol,
    NormalMeasurement,
)
from . import db
from sqlalchemy import or_
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
# *------------------------------------------------------------
# Unified search route to search across the app contetns.
@main_bp.route('/search')
def site_search():
    """Unified search across key WSCompanion models.

    Uses simple ILIKE matching on a set of important text fields
    for each model and returns results grouped by type.
    """
    q = request.args.get('q', '').strip()
    if not q:
        # If empty search, just go home for now
        return redirect(url_for('main_routes.index'))

    like_pattern = f"%{q}%"

    # Search content library
    content_results = (
        db.session.query(Content)
        .filter(
            or_(
                Content.title.ilike(like_pattern),
                Content.description.ilike(like_pattern),
                Content.keywords.ilike(like_pattern),
            )
        )
        .limit(50)
        .all()
    )

    # Search references (only text/string fields)
    refrences_results = (
        db.session.query(Reference)
        .filter(
            or_(
                Reference.title.ilike(like_pattern),
                Reference.description.ilike(like_pattern),
            )
        )
        .limit(50)
        .all()
    )

    # Search imaging protocols (only text/string fields)
    protocol_results = (
        db.session.query(ImagingProtocol)
        .filter(
            or_(
                ImagingProtocol.name.ilike(like_pattern),
                ImagingProtocol.indication.ilike(like_pattern),
                ImagingProtocol.technique_text.ilike(like_pattern),
                ImagingProtocol.contrast_details.ilike(like_pattern),
                ImagingProtocol.tags.ilike(like_pattern),
            )
        )
        .limit(50)
        .all()
    )

    # Search classification systems (only text/string fields)
    classification_results = (
        db.session.query(ClassificationSystem)
        .filter(
            or_(
                ClassificationSystem.name.ilike(like_pattern),
                ClassificationSystem.description.ilike(like_pattern),
                ClassificationSystem.version.ilike(like_pattern),
            )
        )
        .limit(50)
        .all()
    )

    # Search admin report templates (only text/string fields)
    adminreporttemplates_results = (
        db.session.query(AdminReportTemplate)
        .filter(
            or_(
                AdminReportTemplate.template_name.ilike(like_pattern),
                AdminReportTemplate.description.ilike(like_pattern),
                AdminReportTemplate.tags.ilike(like_pattern),
                AdminReportTemplate.category.ilike(like_pattern),
            )
        )
        .limit(50)
        .all()
    )

    # Search user report templates (only text/string fields)
    userreportemplates_results = (
        db.session.query(UserReportTemplate)
        .filter(
            or_(
                UserReportTemplate.template_name.ilike(like_pattern),
                UserReportTemplate.tags.ilike(like_pattern),
                UserReportTemplate.template_text.ilike(like_pattern),
            )
        )
        .limit(50)
        .all()
    )

    # Search normal measurements (only text/string fields)
    measurement_results = (
        db.session.query(NormalMeasurement)
        .filter(
            NormalMeasurement.is_active.is_(True),
            or_(
                NormalMeasurement.name.ilike(like_pattern),
                NormalMeasurement.context.ilike(like_pattern),
                NormalMeasurement.reference_text.ilike(like_pattern),
                NormalMeasurement.tags.ilike(like_pattern),
                NormalMeasurement.age_group.ilike(like_pattern),
                NormalMeasurement.sex.ilike(like_pattern),
            )
        )
        .limit(50)
        .all()
    )

    return render_template(
        'search_results.html',
        query=q,
        content_results=content_results,
        refrences_results=refrences_results,
        protocol_results=protocol_results,
        classification_results=classification_results,
        adminreporttemplates_results=adminreporttemplates_results,
        userreportemplates_results=userreportemplates_results,
        measurement_results=measurement_results,
    )
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
        # Normal measurements
    nm_q = db.session.query(NormalMeasurement).filter(
        NormalMeasurement.is_active.is_(True)
    )

    if selected_modality is not None:
        nm_q = nm_q.filter(NormalMeasurement.modality == selected_modality)

    if selected_body_part is not None:
        nm_q = nm_q.filter(NormalMeasurement.body_part == selected_body_part)

    if query:
        like = f"%{query}%"
        nm_q = nm_q.filter(
            or_(
                NormalMeasurement.name.ilike(like),
                NormalMeasurement.tags.ilike(like),
            )
        )

    normal_measurements = nm_q.order_by(
        NormalMeasurement.modality,
        NormalMeasurement.body_part,
        NormalMeasurement.name,
    ).all()

    # Provide enums for dropdowns
    modality_choices = list(ModalityEnum)
    body_part_choices = list(BodyPartEnum)

    return render_template(
        "radiology_tools.html",
        templates=templates,
        classifications=classifications,
        protocols=protocols,
        normal_measurements=normal_measurements,
        modality_choices=modality_choices,
        body_part_choices=body_part_choices,
        selected_modality=selected_modality,
        selected_body_part=selected_body_part,
        query=query,
    )

# *---------------------------------------------------------------
# Normal measurement library routes
# *---------------------------------------------------------------

@main_bp.route('/measurements')
@login_required
def measurement_library():
    """
    Radiology Measurement Library landing page.
    - Renders the search UI.
    - Results and autocomplete are powered by the JSON API below.
    """
    # Enums are passed so the template can build body-part / modality filters
    return render_template(
        'normal_measurements/measurements_list.html',
        BodyPartEnum=BodyPartEnum,
        ModalityEnum=ModalityEnum,
    )


@main_bp.route('/measurements/<int:measurement_id>')
@login_required
def measurement_detail(measurement_id):
    """
    Pretty detail view for a single normal measurement.
    """
    measurement = (
        db.session.query(NormalMeasurement)
        .filter(
            NormalMeasurement.id == measurement_id,
            NormalMeasurement.is_active.is_(True),
        )
        .first()
    )
    if not measurement:
        # 404 if not found or inactive
        return abort(404)

    return render_template('normal_measurements/measurements_detail.html', m=measurement)


@main_bp.route('/measurements/api/search')
@login_required
def measurements_api_search():
    """
    JSON endpoint for live search & autocomplete of normal measurements.

    Query params:
      - q: free-text query
      - body_part: BodyPartEnum value (optional)
      - modality: ModalityEnum value (optional)
      - diagnosis: text to match in tags (optional)
      - limit: max results (default 20)
    """
    q = (request.args.get('q') or '').strip()
    body_part = (request.args.get('body_part') or '').strip()
    modality = (request.args.get('modality') or '').strip()
    diagnosis = (request.args.get('diagnosis') or '').strip()

    try:
        limit = int(request.args.get('limit', 20))
    except ValueError:
        limit = 20

    query = db.session.query(NormalMeasurement).filter(
        NormalMeasurement.is_active.is_(True)
    )

    if q:
        like = f'%{q}%'
        query = query.filter(
            or_(
                NormalMeasurement.name.ilike(like),
                NormalMeasurement.context.ilike(like),
                NormalMeasurement.reference_text.ilike(like),
                NormalMeasurement.tags.ilike(like),
            )
        )

    if body_part:
        query = query.filter(NormalMeasurement.body_part == body_part)

    if modality:
        query = query.filter(NormalMeasurement.modality == modality)

    if diagnosis:
        like_diag = f'%{diagnosis}%'
        query = query.filter(NormalMeasurement.tags.ilike(like_diag))

    results = (
        query.order_by(NormalMeasurement.name.asc())
        .limit(limit)
        .all()
    )

    def serialize(m):
        # Build display range nicely
        if m.min_value is not None and m.max_value is not None:
            display_range = f"{m.min_value} – {m.max_value} {m.unit or ''}".strip()
        elif m.max_value is not None:
            display_range = f"≤ {m.max_value} {m.unit or ''}".strip()
        elif m.min_value is not None:
            display_range = f"≥ {m.min_value} {m.unit or ''}".strip()
        else:
            display_range = m.unit or ''

        return {
            "id": m.id,
            "name": m.name,
            "body_part": getattr(m.body_part, "value", m.body_part),
            "modality": getattr(m.modality, "value", m.modality),
            "age_group": m.age_group,
            "sex": m.sex,
            "unit": m.unit,
            "display_range": display_range,
            "tags": m.tags,
            "context": m.context,
            "url": url_for('main_routes.measurement_detail', measurement_id=m.id),
        }

    return jsonify({"results": [serialize(m) for m in results]})

#* ----------------------------------------------------------------
# Reporting/Case wrokspace routes
# Section 1: CLinical Question panel.
# Section 2:
# Section 3:

# Section 8:
#* ---------------------------------------------------------------- 
@main_bp.route("/case_workspace", methods=["GET"])
@login_required
def case_workspace():
    """
    Central Case Workspace screen.

    Query params (all optional; can also be set via the form in the template):
      - modality: ModalityEnum.name (e.g. CT, MRI, X_RAY)
      - body_part: BodyPartEnum.name (e.g. LUNG, NEURO)
      - indication: free-text clinical history
      - core_question: short core clinical question (?PE, ?HCC, etc.)
    """

    indication = (request.args.get("indication") or "").strip()
    modality_name = request.args.get("modality")  # e.g. "CT"
    body_part_name = request.args.get("body_part")  # e.g. "LUNG"
    core_question = (request.args.get("core_question") or "").strip()

    modality_enum = None
    body_part_enum = None

    if modality_name:
        try:
            modality_enum = ModalityEnum[modality_name]
        except KeyError:
            flash("Unknown modality selected; please re-select.", "warning")

    if body_part_name:
        try:
            body_part_enum = BodyPartEnum[body_part_name]
        except KeyError:
            flash("Unknown body part selected; please re-select.", "warning")

    # Case context object passed to the template
    case_context = {
        "indication": indication,
        "core_question": core_question,
        "modality_enum": modality_enum,
        "body_part_enum": body_part_enum,
    }

    # --- Auto-suggestions (thin slice for now) ----------------------
    suggested_protocols = []
    suggested_templates = []
    suggested_checklists = []  # placeholder for future checklist model

    if modality_enum and body_part_enum:
        # Protocol suggestions
        suggested_protocols = (
            ImagingProtocol.query
            .filter_by(modality=modality_enum, body_part=body_part_enum)
            .order_by(ImagingProtocol.name.asc())
            .limit(5)
            .all()
        )

        # Report template suggestions
        suggested_templates = (
            AdminReportTemplate.query
            .filter_by(modality=modality_enum, body_part=body_part_enum)
            .order_by(AdminReportTemplate.title.asc())
            .limit(5)
            .all()
        )

        # Later: suggested_checklists from a Checklist/DiagnosisGuide model

    return render_template(
        "case_workspace/case_workspace.html",
        case=case_context,
        modality_choices=list(ModalityEnum),
        body_part_choices=list(BodyPartEnum),
        suggested_protocols=suggested_protocols,
        suggested_templates=suggested_templates,
        suggested_checklists=suggested_checklists,
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
