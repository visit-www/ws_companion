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
    ModuleNames,
)
from . import db
from .util import (
    get_case_templates,
    get_case_classifications,
    get_case_measurements,
    get_case_checklists,
    _clean_search_text,
    _body_part_matches,
    render_report_template_to_text,
)
from sqlalchemy import or_, func
from flask_cors import CORS
from flask_login import current_user, AnonymousUserMixin, login_required
from config import userdir, creativesfolder
from types import SimpleNamespace

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

    Uses normalised (hyphen/space-insensitive) matching on a set of important text fields
    for each model and returns results grouped by type.
    """
    q = request.args.get('q', '').strip()
    if not q:
        # If empty search, just go home for now
        return redirect(url_for('main_routes.index'))

    # Normalise the query for hyphen/space-insensitive matching:
    # e.g. "ti-rads" -> "tirads", "ct pa" -> "ctpa"
    norm_q = re.sub(r"[\s\-]+", "", q.lower())
    if not norm_q:
        return redirect(url_for('main_routes.index'))

    def norm_match(col):
        """
        Apply the same normalisation to a text column as to the query:
        - lower-case
        - remove spaces
        - remove hyphens
        Then run a LIKE '%norm_q%'.
        """
        lowered = func.lower(col)
        no_hyphen = func.replace(lowered, "-", "")
        no_space = func.replace(no_hyphen, " ", "")
        return no_space.like(f"%{norm_q}%")

    # Search content library
    content_results = (
        db.session.query(Content)
        .filter(
            or_(
                norm_match(Content.title),
                norm_match(Content.description),
                norm_match(Content.keywords),
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
                norm_match(Reference.title),
                norm_match(Reference.description),
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
                norm_match(ImagingProtocol.name),
                norm_match(ImagingProtocol.indication),
                norm_match(ImagingProtocol.technique_text),
                norm_match(ImagingProtocol.contrast_details),
                norm_match(ImagingProtocol.tags),
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
                norm_match(ClassificationSystem.name),
                norm_match(ClassificationSystem.description),
                norm_match(ClassificationSystem.version),
            )
        )
        .limit(50)
        .all()
    )

    # Search admin report templates
    adminreporttemplates_results = (
        db.session.query(AdminReportTemplate)
        .filter(
            or_(
                norm_match(AdminReportTemplate.template_name),
                norm_match(AdminReportTemplate.description),
                norm_match(AdminReportTemplate.tags),
            )
        )
        .limit(50)
        .all()
    )

    # Search user report templates
    userreportemplates_results = (
        db.session.query(UserReportTemplate)
        .filter(
            or_(
                norm_match(UserReportTemplate.template_name),
                norm_match(UserReportTemplate.tags),
            )
        )
        .limit(50)
        .all()
    )

    # Search normal measurements
    measurement_results = (
        db.session.query(NormalMeasurement)
        .filter(
            or_(
                norm_match(NormalMeasurement.name),
                norm_match(NormalMeasurement.context),
                norm_match(NormalMeasurement.reference_text),
                norm_match(NormalMeasurement.tags),
                norm_match(NormalMeasurement.age_group),
                norm_match(NormalMeasurement.sex),
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
def _rank_case_protocols(indication, core_question, modality_enum, body_part_enum, module_enum, limit=5):
    """Rank ImagingProtocol rows for the Case Workspace.

    Updated Phase 1.5 strategy (radiologist-centric):
    - Modality and body_part are the primary structural gates.
    - Module is a soft refiner:
      * Prefer protocols whose module matches the selected module.
      * If filtering by module would remove all candidates, fall back to the
        broader structural set.
    - Text filters:
      * core_question is the primary textual driver.
        - If some protocols match core tokens, show only those.
        - If none match, fall back to the structural set (do NOT return empty).
      * If no core_question but indication is present, use indication tokens
        in the same way, but with weaker weight.
      * If neither core_question nor indication is provided, return the
        structural set ordered by modality/body_part/name.
    """

    # 1) Load all active protocols once
    base_query = db.session.query(ImagingProtocol).filter(
        ImagingProtocol.is_active.is_(True)
    )
    all_protocols = base_query.all()

    # 2) Structural gating: modality + body_part via _body_part_matches
    structural_candidates = []
    for proto in all_protocols:
        # Modality gate
        if modality_enum is not None and proto.modality != modality_enum:
            continue

        # Body-part gate (using the shared body-part matcher)
        if body_part_enum is not None and not _body_part_matches(proto.body_part, body_part_enum):
            continue

        structural_candidates.append(proto)

    # If no structural candidates at all, stop early
    if not structural_candidates:
        return []

    # 3) Optional module refinement: try to narrow to matching module,
    #    but never drop to an empty set solely because of module.
    module_filtered = structural_candidates
    if module_enum is not None:
        narrowed = [
            p for p in structural_candidates
            if getattr(p, "module", None) == module_enum
        ]
        if narrowed:
            module_filtered = narrowed

    # 4) Clean and tokenise text inputs
    cleaned_core = _clean_search_text(core_question) if core_question else ""
    cleaned_indication = _clean_search_text(indication) if indication else ""
    core_tokens = _tokenize(cleaned_core)
    indication_tokens = _tokenize(cleaned_indication)

    # 5) Score all module-filtered candidates
    scored = []
    for proto in module_filtered:
        text_blob_parts = [
            proto.name or "",
            proto.indication or "",
            proto.tags or "",
        ]
        text_blob = " ".join(text_blob_parts).lower()
        blob_tokens = set(_tokenize(text_blob))

        core_hits = sum(1 for tok in core_tokens if tok and tok in blob_tokens)
        indication_hits = sum(1 for tok in indication_tokens if tok and tok in blob_tokens)

        score = 0

        # Structural reinforcement
        if modality_enum is not None and proto.modality == modality_enum:
            score += 5
        if body_part_enum is not None and _body_part_matches(proto.body_part, body_part_enum):
            score += 5

        # Module bonus (soft preference)
        if module_enum is not None and getattr(proto, "module", None) == module_enum:
            score += 3

        # Textual components: core is strong, indication is softer
        score += core_hits * 4
        score += indication_hits * 1

        scored.append((score, proto, core_hits, indication_hits))

    # 6) Apply text-driven filtering according to the rules
    bucket = []

    if core_tokens:
        # Prefer protocols that actually mention the core question tokens
        core_only = [(s, p) for (s, p, ch, ih) in scored if ch > 0]
        if core_only:
            bucket = core_only
        else:
            # No protocol textually matches the core question: fall back to
            # the full structural/module-filtered set (do not return empty).
            bucket = [(s, p) for (s, p, ch, ih) in scored]
    elif indication_tokens:
        # No core question, but we do have indication text
        ind_only = [(s, p) for (s, p, ch, ih) in scored if ih > 0]
        if ind_only:
            bucket = ind_only
        else:
            # Indication text didn't narrow anything: show structural set
            bucket = [(s, p) for (s, p, ch, ih) in scored]
    else:
        # No core_question or indication: pure structural ordering
        bucket = [(s, p) for (s, p, ch, ih) in scored]

    # 7) Sort by score desc, then name for stability and apply limit
    bucket.sort(key=lambda item: (-item[0], item[1].name or ""))

    return [proto for score, proto in bucket[:limit]]
#-----------------------
    
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
    tool_search = (request.args.get("tool_search") or "").strip()

    source = (request.args.get("source") or "left").strip()

    # Optional: selected report template for Phase 2 reporting workspace
    selected_admin_template_id = request.args.get("admin_template_id")
    selected_user_template_id = request.args.get("user_template_id")

    active_template = None
    report_text_default = ""

    # Prefer a user template if explicitly selected
    if selected_user_template_id:
        # In the current schema the primary key is an integer. Guard against
        # invalid/non-numeric IDs coming from the query string so we don't
        # trigger a DataError on the database.
        tpl = None
        try:
            user_tpl_id_int = int(selected_user_template_id)
        except (TypeError, ValueError):
            user_tpl_id_int = None
        if user_tpl_id_int is not None:
            tpl = db.session.get(UserReportTemplate, user_tpl_id_int)

        if tpl is not None:
            # Resolve user template body using the universal renderer
            tpl_body = render_report_template_to_text(tpl, export_scope="case_workspace")

            active_template = SimpleNamespace(
                kind="user",
                id=tpl.id,
                name=tpl.template_name,
                modality=tpl.modality,
                body_part=tpl.body_part,
                module=getattr(tpl, "module", None),
                tags=tpl.tags,
                template_text=tpl_body,
                definition_json=getattr(tpl, "definition_json", None),
            )

    # If no user template, fall back to an admin (WSCompanion) template
    if active_template is None and selected_admin_template_id:
        try:
            admin_tpl_id_int = int(selected_admin_template_id)
        except ValueError:
            admin_tpl_id_int = None
        if admin_tpl_id_int is not None:
            tpl = db.session.query(AdminReportTemplate).get(admin_tpl_id_int)
            if tpl is not None:
                # Resolve admin template body using the universal renderer
                tpl_body = render_report_template_to_text(tpl, export_scope="case_workspace")

                active_template = SimpleNamespace(
                    kind="admin",
                    id=tpl.id,
                    name=tpl.template_name,
                    modality=tpl.modality,
                    body_part=tpl.body_part,
                    module=getattr(tpl, "module", None),
                    tags=tpl.tags,
                    template_text=tpl_body,
                    definition_json=getattr(tpl, "definition_json", None),
                )

    if active_template is not None:
        # Use whatever body we resolved from the selected template (user or admin)
        report_text_default = getattr(active_template, "template_text", "") or ""
    # Decide which text field actually drives the smart suggestions:
    # - If the request came from the right-panel tool search, use tool_search
    #   as the primary driver and ignore indication/core_question.
    # - Otherwise (default/left panel), ignore tool_search for ranking and
    #   rely on indication + core_question as before.
    if source == "right" and tool_search:
        ranking_core_question = tool_search
        ranking_indication = ""
    else:
        ranking_core_question = core_question
        ranking_indication = indication
        # Do not let a stale tool_search accidentally influence anything
        tool_search = ""

    module_name = request.args.get("module")  # e.g. "CHEST", "GASTROINTESTINAL"
    module_enum = None

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

    if module_name:
        try:
            module_enum = ModuleNames[module_name]
        except KeyError:
            flash("Unknown module selected; please re-select.", "warning")

    # For ranking, we may ignore structural gates when searching from the right panel.
    suggest_modality_enum = modality_enum
    suggest_body_part_enum = body_part_enum
    suggest_module_enum = module_enum

    # If the request originated from the right-panel tool search, we want a
    # "pure tool search" that does not depend on left-panel structural inputs.
    # In that case, disable structural gating for the ranking helpers.
    if source == "right":
        suggest_modality_enum = None
        suggest_body_part_enum = None
        suggest_module_enum = None

    # (active_template and report_text_default are now constructed above)

    case_context = {
        "indication": indication,
        "core_question": core_question,
        "modality_enum": modality_enum,
        "body_part_enum": body_part_enum,
        "module_enum": module_enum,
        "tool_search": tool_search,
        "source": source,
    }

    # --- Auto-suggestions (thin slice for now) ----------------------
    suggested_protocols = []
    suggested_user_templates = []
    suggested_admin_templates = []
    suggested_classifications = []
    suggested_checklists = []  # placeholder for future checklist model
    suggested_measurements = []

    # Branch 1: Right-panel tool search → pure tool-centric search using
    # the same normalised matching logic as the global site_search, but
    # returning results into the Case Workspace suggestion slots.
    if source == "right" and tool_search:
        norm_q = re.sub(r"[\s\-]+", "", tool_search.lower())

        if norm_q:
            def norm_match_case(col):
                lowered = func.lower(col)
                no_hyphen = func.replace(lowered, "-", "")
                no_space = func.replace(no_hyphen, " ", "")
                return no_space.like(f"%{norm_q}%")

            # Imaging protocols (no structural gating; pure tool search)
            suggested_protocols = (
                db.session.query(ImagingProtocol)
                .filter(
                    ImagingProtocol.is_active.is_(True),
                    or_(
                        norm_match_case(ImagingProtocol.name),
                        norm_match_case(ImagingProtocol.indication),
                        norm_match_case(ImagingProtocol.technique_text),
                        norm_match_case(ImagingProtocol.contrast_details),
                        norm_match_case(ImagingProtocol.tags),
                    ),
                )
                .order_by(ImagingProtocol.modality, ImagingProtocol.body_part, ImagingProtocol.name)
                .limit(10)
                .all()
            )

            # Admin report templates
            suggested_admin_templates = (
                db.session.query(AdminReportTemplate)
                .filter(
                    AdminReportTemplate.is_active.is_(True),
                    or_(
                        norm_match_case(AdminReportTemplate.template_name),
                        norm_match_case(AdminReportTemplate.description),
                        norm_match_case(AdminReportTemplate.tags),
                    ),
                )
                .order_by(AdminReportTemplate.modality, AdminReportTemplate.body_part, AdminReportTemplate.template_name)
                .limit(10)
                .all()
            )

            # User-specific report templates
            if isinstance(current_user, AnonymousUserMixin):
                suggested_user_templates = []
            else:
                suggested_user_templates = (
                    db.session.query(UserReportTemplate)
                    .filter(
                        UserReportTemplate.user_id == current_user.id,
                        or_(
                            norm_match_case(UserReportTemplate.template_name),
                            norm_match_case(UserReportTemplate.tags),
                        ),
                    )
                    .order_by(UserReportTemplate.updated_at.desc())
                    .limit(10)
                    .all()
                )

            # Classification / staging systems
            suggested_classifications = (
                db.session.query(ClassificationSystem)
                .filter(
                    ClassificationSystem.is_active.is_(True),
                    or_(
                        norm_match_case(ClassificationSystem.name),
                        norm_match_case(ClassificationSystem.description),
                        norm_match_case(ClassificationSystem.version),
                    ),
                )
                .order_by(ClassificationSystem.category, ClassificationSystem.name)
                .limit(10)
                .all()
            )

            # Normal measurements
            suggested_measurements = (
                db.session.query(NormalMeasurement)
                .filter(
                    NormalMeasurement.is_active.is_(True),
                    or_(
                        norm_match_case(NormalMeasurement.name),
                        norm_match_case(NormalMeasurement.context),
                        norm_match_case(NormalMeasurement.reference_text),
                        norm_match_case(NormalMeasurement.tags),
                        norm_match_case(NormalMeasurement.age_group),
                        norm_match_case(NormalMeasurement.sex),
                    ),
                )
                .order_by(NormalMeasurement.modality, NormalMeasurement.body_part, NormalMeasurement.name)
                .limit(10)
                .all()
            )

            # Checklists remain a placeholder for now (no model yet)

    # Branch 2: Left-panel (or default) case navigator →
    # use the Phase 1.5 structural + clinical strategy.
    else:
        # Decide when to run suggestions:
        # - Requires at least one structural driver (modality/body_part).
        run_suggestions = False
        if suggest_modality_enum or suggest_body_part_enum:
            run_suggestions = True

        if run_suggestions:
            # Protocol suggestions (Phase 1.5 smart ranking)
            suggested_protocols = _rank_case_protocols(
                indication=ranking_indication,
                core_question=ranking_core_question,
                modality_enum=suggest_modality_enum,
                body_part_enum=suggest_body_part_enum,
                module_enum=suggest_module_enum,
                limit=5,
            )

            # Report template suggestions (user + admin)
            suggested_user_templates, suggested_admin_templates = get_case_templates(
                suggest_modality_enum,
                suggest_body_part_enum,
                user_id=current_user.id,
                limit=8,
                indication=ranking_indication,
                core_question=ranking_core_question,
                module=suggest_module_enum,
            )

            # Staging / classification suggestions
            suggested_classifications = get_case_classifications(
                suggest_modality_enum,
                suggest_body_part_enum,
                indication=ranking_indication,
                core_question=ranking_core_question,
                limit=8,
                module=suggest_module_enum,
            )

            # Measurement suggestions (Phase 1 smart ranking)
            suggested_measurements = get_case_measurements(
                modality=suggest_modality_enum,
                body_part=suggest_body_part_enum,
                indication=ranking_indication,
                core_question=ranking_core_question,
                limit=8,
                module=suggest_module_enum,
            )

            # Checklist suggestions (Phase 1 placeholder)
            suggested_checklists = get_case_checklists(
                modality=suggest_modality_enum,
                body_part=suggest_body_part_enum,
                indication=ranking_indication,
                core_question=ranking_core_question,
                limit=8,
            )
        # -----------------------------------------
    return render_template(
        "case_workspace/case_workspace.html",
        case=case_context,
        modality_choices=list(ModalityEnum),
        body_part_choices=list(BodyPartEnum),
        module_choices=list(ModuleNames),
        suggested_protocols=suggested_protocols,
        suggested_user_templates=suggested_user_templates,
        suggested_admin_templates=suggested_admin_templates,
        suggested_classifications=suggested_classifications,
        suggested_checklists=suggested_checklists,
        suggested_measurements=suggested_measurements,
        module_enum=module_enum,
        tool_search=tool_search,
        active_template=active_template,
        report_text_default=report_text_default,
    )


# ---------------------------------------
@main_bp.route("/case_workspace/save_report_instance", methods=["POST"])
@login_required
def save_report_instance():
    """Persist a single Phase 2 report draft as a UserReportInstance.

    This is intentionally lightweight for now: it anchors a saved report to
    the current user, the chosen template (user/admin), and the structural
    case context (modality/body_part/module + indication/core_question).
    """
    from .models import UserReportInstance, ModalityEnum, BodyPartEnum, ModuleNames

    form = request.form

    # Basic required fields
    report_text = (form.get("report_text") or "").strip()
    diagnosis = (form.get("diagnosis") or "").strip()

    if not report_text or not diagnosis:
        flash("Report text and diagnosis are required to save a report instance.", "warning")
        # Fall back to reloading the case workspace with whatever structural context we have
        indication = form.get("indication", "")
        modality_name = form.get("modality", "")
        body_part_name = form.get("body_part", "")
        module_name = form.get("module", "")
        core_question = form.get("core_question", "")

        return redirect(
            url_for(
                "main_routes.case_workspace",
                indication=indication,
                modality=modality_name,
                body_part=body_part_name,
                module=module_name,
                core_question=core_question,
            )
        )

    # Optional meta fields
    institution_name = (form.get("institution_name") or "").strip() or None
    service_name = (form.get("service_name") or "").strip() or None

    # Structural context
    indication = (form.get("indication") or "").strip() or None
    core_question = (form.get("core_question") or "").strip() or None

    modality_name = form.get("modality") or None
    body_part_name = form.get("body_part") or None
    module_name = form.get("module") or None

    modality_enum = None
    body_part_enum = None
    module_enum = None

    if modality_name:
        try:
            modality_enum = ModalityEnum[modality_name]
        except KeyError:
            modality_enum = None

    if body_part_name:
        try:
            body_part_enum = BodyPartEnum[body_part_name]
        except KeyError:
            body_part_enum = None

    if module_name:
        try:
            module_enum = ModuleNames[module_name]
        except KeyError:
            module_enum = None

    # Template linkage
    template_kind = form.get("active_template_kind") or None
    template_id_raw = form.get("active_template_id") or None
    admin_template_id = None
    user_template_id = None

    if template_kind and template_id_raw:
        try:
            template_id_int = int(template_id_raw)
        except ValueError:
            template_id_int = None

        # For now we assume:
        #   kind == 'admin' -> admin_template_id (integer PK)
        #   kind == 'user'  -> user_template_id (UUID string)
        if template_kind == "admin" and template_id_int is not None:
            admin_template_id = template_id_int
        elif template_kind == "user":
            # UserReportTemplate primary key is UUID (string/UUID depending on model)
            user_template_id = template_id_raw

    instance = UserReportInstance(
        user_id=current_user.id,
        admin_template_id=admin_template_id,
        user_template_id=user_template_id,
        modality=modality_enum,
        body_part=body_part_enum,
        module=module_enum,
        diagnosis=diagnosis,
        institution_name=institution_name,
        service_name=service_name,
        indication=indication,
        core_question=core_question,
        report_text=report_text,
    )

    db.session.add(instance)
    db.session.commit()

    flash("Report instance saved to your personal library.", "success")

    return redirect(
        url_for(
            "main_routes.case_workspace",
            indication=indication or "",
            modality=modality_name or "",
            body_part=body_part_name or "",
            module=module_name or "",
            core_question=core_question or "",
        )
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
    message = ("The function failed- Thats why you are seeing this page!")
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

    if not os.path.exists(file_path):
        return abort(404)

    try:
        return send_file(file_path, as_attachment=False)
    except Exception:
        return abort(403)
