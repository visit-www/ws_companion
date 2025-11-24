from flask import Blueprint, render_template, jsonify, request, flash, send_from_directory, redirect, url_for
from flask_wtf.csrf import generate_csrf
import re
from .models import (
    Content,
    User,
    AdminReportTemplate,
    ClassificationSystem,
    ImagingProtocol,
    CategoryNames,
    UserData,
    Reference,
    ModalityEnum,
    BodyPartEnum,
    NormalMeasurement,
    UserReportTemplate,
)
from . import db
from .util import (
    get_case_templates,
    get_case_classifications,
    get_case_measurements,
    get_case_checklists,
    _clean_search_text,
)
from sqlalchemy import or_
from flask_cors import CORS
from flask_login import current_user, AnonymousUserMixin, login_required
from config import userdir, creativesfolder

#----------------------------------------------------------------
# Helper: simple tokenizer for smart search
def _tokenize(text):
    """
    Simple helper to normalise and split free-text into tokens.
    Used by Case Workspace smart search.
    """
    if not text:
        return []
    tokens = re.split(r"\W+", text.lower())
    return [t for t in tokens if len(t) >= 2]

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

    # Search admin report templates (category is now enum)
    adminreporttemplates_results = (
        db.session.query(AdminReportTemplate)
        .filter(
            or_(
                AdminReportTemplate.template_name.ilike(like_pattern),
                AdminReportTemplate.description.ilike(like_pattern),
                AdminReportTemplate.tags.ilike(like_pattern),
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

# *---------------------------------------------------------------
# Normal Measurements Library route
@main_bp.route("/measurement-library", methods=["GET"])
@login_required
def measurement_library():
    """
    Landing page for the Normal Measurements library.

    For now this is a simple read-only list with optional free-text search,
    reusing the NormalMeasurement model. Later we can extend it with
    modality/body-part filters and tighter integration with the Case Workspace.
    """
    query = request.args.get("q") or ""

    measurements_q = db.session.query(NormalMeasurement)

    if query:
        like = f"%{query}%"
        measurements_q = measurements_q.filter(
            or_(
                NormalMeasurement.name.ilike(like),
                NormalMeasurement.context.ilike(like),
                NormalMeasurement.reference_text.ilike(like),
                NormalMeasurement.tags.ilike(like),
                NormalMeasurement.age_group.ilike(like),
                NormalMeasurement.sex.ilike(like),
            )
        )

    measurements = measurements_q.order_by(NormalMeasurement.name.asc()).all()

    return render_template(
        "measurement_library.html",
        measurements=measurements,
        query=query,
    )

# *---------------------------------------------------------------
# Helper: Rank ImagingProtocols for Case Workspace
def _rank_case_protocols(indication, core_question, modality_enum, body_part_enum, limit=5):
    """Rank ImagingProtocol rows for the Case Workspace.

    Strategy:
    - Structural filters (modality/body_part) are hard gates.
      * If BOTH modality and body_part are provided, only protocols matching BOTH
        are allowed. If none match, return [].
      * If only modality OR only body_part is provided, structural filter uses
        that dimension alone. If none match, return [].
      * If neither is provided, all active protocols are structurally allowed.
    - Text filters (within the structurally-matched set):
      * core_question (cleaned) is the primary driver.
      * If no core match, fall back to indication (cleaned) if present.
      * If neither core nor indication match anything, fall back to the
        structural set (modality/body_part only).
    """

    # 1) Load all active protocols once
    base_query = db.session.query(ImagingProtocol).filter(
        ImagingProtocol.is_active.is_(True)
    )
    all_protocols = base_query.all()

    # Helper: loose body part match (Phase 1 simple version)
    def _body_part_matches(proto_bp, selected_bp):
        if selected_bp is None:
            return True
        if proto_bp is None:
            return False
        if proto_bp == selected_bp:
            return True
        # Loose match for abdomen-style regions (Phase 1 simple heuristic)
        try:
            name = proto_bp.name.upper()
            sel = selected_bp.name.upper()
        except AttributeError:
            return False

        # If user picks ABDOMEN, also accept enums whose names include
        # "ABDOMEN" or "GI" (e.g. UPPER_GI, LOWER_GI) as a loose match.
        if sel == "ABDOMEN":
            if "ABDOMEN" in name or "GI" in name:
                return True
        # Add other loose mappings later as needed (Phase 1.5)
        return False

    def _modality_matches(proto_mod, selected_mod):
        if selected_mod is None:
            return True
        if proto_mod is None:
            return False
        return proto_mod == selected_mod

    # 2) Structural gating
    structural_candidates = []

    for proto in all_protocols:
        mod_ok = _modality_matches(proto.modality, modality_enum)
        bp_ok = _body_part_matches(proto.body_part, body_part_enum)

        if modality_enum and body_part_enum:
            # Both required: only keep if BOTH match
            if mod_ok and bp_ok:
                structural_candidates.append(proto)
        elif modality_enum:
            if mod_ok:
                structural_candidates.append(proto)
        elif body_part_enum:
            if bp_ok:
                structural_candidates.append(proto)
        else:
            # No structural driver at all: allow everything
            structural_candidates.append(proto)

    # If there was any structural driver but no candidates, stop early
    if (modality_enum or body_part_enum) and not structural_candidates:
        print("=== _rank_case_protocols: no structural candidates for given modality/body_part; returning empty list ===")
        return []

    # If no structural driver and nothing active, nothing to do
    if not structural_candidates:
        return []

    # 3) Clean and tokenise text inputs
    cleaned_core = _clean_search_text(core_question) if core_question else ""
    cleaned_indication = _clean_search_text(indication) if indication else ""
    core_tokens = _tokenize(cleaned_core)
    indication_tokens = _tokenize(cleaned_indication)

    print("=== _rank_case_protocols context ===")
    print(f"  indication={indication!r}")
    print(f"  core_question={core_question!r}")
    print(f"  modality_enum={modality_enum}")
    print(f"  body_part_enum={body_part_enum}")
    print(f"  cleaned_core={cleaned_core!r}")
    print(f"  cleaned_indication={cleaned_indication!r}")
    print(f"  core_tokens={core_tokens}")
    print(f"  indication_tokens={indication_tokens}")

    # 4) Textual filtering within the structural set
    core_matches_list = []
    indication_matches_list = []
    structural_only = []

    for proto in structural_candidates:
        text_blob_parts = [
            proto.name or "",
            proto.indication or "",
            proto.tags or "",
        ]
        text_blob = " ".join(text_blob_parts).lower()
        blob_tokens = set(_tokenize(text_blob))

        core_match_count = 0
        for tok in core_tokens:
            if tok and tok in blob_tokens:
                core_match_count += 1

        indication_match_count = 0
        for tok in indication_tokens:
            if tok and tok in blob_tokens:
                indication_match_count += 1

        # Simple score for sorting: core matches (strong), indication (soft)
        score = core_match_count * 4 + indication_match_count * 1

        if core_tokens and core_match_count > 0:
            core_matches_list.append((score, proto))
        elif (not core_tokens) and indication_tokens and indication_match_count > 0:
            indication_matches_list.append((score, proto))
        else:
            structural_only.append((score, proto))

    # 5) Decide which bucket to use
    if core_tokens and core_matches_list:
        bucket = core_matches_list
    elif indication_tokens and indication_matches_list:
        bucket = indication_matches_list
    else:
        # Fall back to purely structural candidates (even if scores are 0)
        bucket = structural_only

    # 6) Sort by score desc, then name for stability
    bucket.sort(key=lambda item: (-item[0], item[1].name or ""))

    return [proto for score, proto in bucket[:limit]]

# Case Workspace route
@main_bp.route("/case_workspace", methods=["GET"])
@login_required
def case_workspace():
    """
    Central Case Workspace screen.

    Query params (all optional; can also be set via the form in the template):
      - modality: ModalityEnum.name (e.g. CT, MRI)
      - body_part: BodyPartEnum.name (e.g. LUNG, NEURO)
      - indication: free-text clinical history (also used to drive smart suggestions)
      - core_question: short core clinical question (?PE, ?HCC, etc.)

    Phase 1 goal:
    Use the combination of indication + modality + body_part + core_question
    to propose the most relevant protocols / templates / classifications
    in the right-hand Case Navigator panel.
    """

    indication = (request.args.get("indication") or "").strip()
    modality_name = request.args.get("modality")     # e.g. "CT"
    body_part_name = request.args.get("body_part")   # e.g. "LUNG"
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

    # Enforce: at least one of modality, body part, or core question must be provided
    if not modality_enum and not body_part_enum and not core_question:
        flash(
            "Please select at least a modality, body part, or enter a core question to update the workspace.",
            "warning",
        )

    case_context = {
        "indication": indication,
        "core_question": core_question,
        "modality_enum": modality_enum,
        "body_part_enum": body_part_enum,
    }

    # --- Auto-suggestions (thin slice for now) ----------------------
    suggested_protocols = []
    suggested_user_templates = []
    suggested_admin_templates = []
    suggested_classifications = []
    suggested_checklists = []  # placeholder for future checklist model
    suggested_measurements = []

    # Only attempt suggestions if at least one driver is present
    if modality_enum or body_part_enum or core_question or indication:
        # Protocol suggestions (Phase 1 smart ranking)
        suggested_protocols = _rank_case_protocols(
            indication=indication,
            core_question=core_question,
            modality_enum=modality_enum,
            body_part_enum=body_part_enum,
            limit=5,
        )

        # Report template suggestions (user + admin)
        suggested_user_templates, suggested_admin_templates = get_case_templates(
            modality_enum,
            body_part_enum,
            user_id=current_user.id,
            limit=8,
            indication=indication,
            core_question=core_question,
        )
        # Staging / classification suggestions
        suggested_classifications = get_case_classifications(
            modality_enum,
            body_part_enum,
            indication=indication,
            core_question=core_question,
            limit=8,
        )

        # Measurement suggestions (Phase 1 smart ranking)
        suggested_measurements = get_case_measurements(
            modality=modality_enum,
            body_part=body_part_enum,
            indication=indication,
            core_question=core_question,
            limit=8,
        )

        # Checklist suggestions (Phase 1 placeholder)
        suggested_checklists = get_case_checklists(
            modality=modality_enum,
            body_part=body_part_enum,
            indication=indication,
            core_question=core_question,
            limit=8,
        )

    return render_template(
        "case_workspace/case_workspace.html",
        case=case_context,
        modality_choices=list(ModalityEnum),
        body_part_choices=list(BodyPartEnum),
        suggested_protocols=suggested_protocols,
        suggested_user_templates=suggested_user_templates,
        suggested_admin_templates=suggested_admin_templates,
        suggested_classifications=suggested_classifications,
        suggested_checklists=suggested_checklists,
        suggested_measurements=suggested_measurements,
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
