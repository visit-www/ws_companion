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
    UserReportInstance,
    SmartHelperCard,
    SmartHelperSectionEnum,
    SmartHelperKindEnum,
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
    serialize_smart_helper_card,
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

#----------------------------------------------------------------
# Phase 2c/3/4: unified diagnosis suggestion pipeline
#----------------------------------------------------------------

# Minimal static playbook so the helper is useful even with little app data.
# Keys are (ModalityEnum.name, BodyPartEnum.name, canonical_core_key).
SMART_DIAGNOSIS_SUGGESTION_PLAYBOOK = {
    ("CT", "LUNG", "PE"): [
        "Acute pulmonary embolism",
        "Submassive pulmonary embolism",
        "No CT evidence of pulmonary embolism",
    ],
    ("CT", "LUNG", "ILD"): [
        "HRCT pattern most consistent with UIP",
        "HRCT pattern indeterminate for UIP",
        "No CT evidence of fibrotic interstitial lung disease",
    ],
    ("CT", "ABDOMEN", "APPENDICITIS"): [
        "Acute uncomplicated appendicitis",
        "Acute complicated appendicitis with perforation",
        "No CT evidence of appendicitis",
    ],
    ("MRI", "SPINE", "CES"): [
        "Large central disc prolapse with cauda equina compression",
        "Multilevel degenerative canal stenosis – no definite cauda equina compression",
        "No MRI evidence of cauda equina compression",
    ],
}


def _canonical_core_question_key(core_question: str) -> str:
    """
    Map a free-text core clinical question to a small set of canonical keys
    used by the static diagnosis playbook.

    This is intentionally conservative and can be expanded gradually as needed.
    """
    if not core_question:
        return ""

    text = core_question.lower()

    # Pulmonary embolism
    if "pulmonary embol" in text or "pe" in text:
        return "PE"

    # Interstitial lung disease / fibrosis / UIP
    if "ild" in text or "interstitial" in text or "fibrosis" in text or "uip" in text:
        return "ILD"

    # Appendicitis / appendix
    if "appendicitis" in text or "appendix" in text or "rlq" in text:
        return "APPENDICITIS"

    # Cauda equina syndrome
    if "cauda equina" in text or "ces" in text:
        return "CES"

    return ""


def _pull_user_history_diagnosis_labels(context, user):
    """
    Tier A source: user's own saved report instances.

    Returns a list of diagnosis strings (duplicates and empties are filtered
    later in the aggregate step).
    """
    if isinstance(user, AnonymousUserMixin):
        return []

    modality_enum = context.get("modality_enum")
    body_part_enum = context.get("body_part_enum")

    q = db.session.query(UserReportInstance).filter(
        UserReportInstance.user_id == user.id
    )

    if modality_enum is not None:
        q = q.filter(UserReportInstance.modality == modality_enum)
    if body_part_enum is not None:
        q = q.filter(UserReportInstance.body_part == body_part_enum)

    q = q.filter(UserReportInstance.diagnosis.isnot(None))

    rows = q.order_by(UserReportInstance.id.desc()).limit(30).all()
    return [row.diagnosis for row in rows if row.diagnosis]


def _pull_template_diagnosis_labels(context, user):
    """
    Tier A source: admin and user report templates whose names can act as
    diagnosis labels for the current structural context.
    """
    modality_enum = context.get("modality_enum")
    body_part_enum = context.get("body_part_enum")
    module_enum = context.get("module_enum")

    suggestions = []

    # Admin templates
    tpl_q = db.session.query(AdminReportTemplate).filter(
        AdminReportTemplate.is_active.is_(True)
    )
    if modality_enum is not None:
        tpl_q = tpl_q.filter(AdminReportTemplate.modality == modality_enum)
    if body_part_enum is not None:
        tpl_q = tpl_q.filter(AdminReportTemplate.body_part == body_part_enum)
    if module_enum is not None:
        tpl_q = tpl_q.filter(AdminReportTemplate.module == module_enum)

    for tpl in tpl_q.limit(20).all():
        if tpl.template_name:
            suggestions.append(tpl.template_name)

    # User templates (if logged in)
    if not isinstance(user, AnonymousUserMixin):
        utpl_q = db.session.query(UserReportTemplate).filter(
            UserReportTemplate.user_id == user.id
        )
        if modality_enum is not None:
            utpl_q = utpl_q.filter(UserReportTemplate.modality == modality_enum)
        if body_part_enum is not None:
            utpl_q = utpl_q.filter(UserReportTemplate.body_part == body_part_enum)
        if module_enum is not None:
            utpl_q = utpl_q.filter(UserReportTemplate.module == module_enum)

        for tpl in utpl_q.limit(20).all():
            if tpl.template_name:
                suggestions.append(tpl.template_name)

    return suggestions


def _pull_playbook_diagnosis_labels(context):
    """
    Tier B source: static, curated diagnosis labels keyed by modality/body-part/core.
    """
    modality_enum = context.get("modality_enum")
    body_part_enum = context.get("body_part_enum")
    core_question = context.get("core_question") or ""

    if modality_enum is None or body_part_enum is None:
        return []

    core_key = _canonical_core_question_key(core_question)
    if not core_key:
        return []

    key = (modality_enum.name, body_part_enum.name, core_key)
    return SMART_DIAGNOSIS_SUGGESTION_PLAYBOOK.get(key, [])


    # Core helper for Phase 2c/3/4:
    # Given structural context + user, build a short list of smart diagnosis
    # suggestion labels by aggregating from history, templates and playbook.
def build_smart_diagnosis_suggestions(context, user):
    """
    Unified helper used by Phase 2c/3/4 diagnosis suggestion endpoint.

    It aggregates suggestions from several tiers:

    - User history and templates (Tier A, deterministic).
    - Static playbook (Tier B, deterministic).
    - Optional AI helper (Tier C, future; not implemented yet).

    Returns a short, de-duplicated list of candidate diagnosis labels.
    """
    suggestions = []

    # Tier A: personal/app content
    suggestions.extend(_pull_user_history_diagnosis_labels(context, user))
    suggestions.extend(_pull_template_diagnosis_labels(context, user))

    # Tier B: static playbook for thin-slice coverage
    if len(suggestions) < 3:
        suggestions.extend(_pull_playbook_diagnosis_labels(context))

    # Tier C (AI) intentionally omitted for now – will be added in Phase 4.

    # Normalise, dedupe (case-insensitive) and truncate
    seen = set()
    cleaned = []
    for text in suggestions:
        if not text:
            continue
        norm = text.strip()
        if not norm:
            continue
        key = norm.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(norm)

    return cleaned[:6]

#----------------------------------------------------------------
# Phase 2c: generic smart helper cards (section + selection)
#----------------------------------------------------------------

# Reusable helper card definitions (so we can attach them to multiple sections).
WELLS_PE_HELPER_CARD = {
    "kind": "SCORE_SUMMARY",
    "title": "Wells score for pulmonary embolism",
    "summary": "Clinical prediction rule estimating pre-test probability of pulmonary embolism.",
    "bullets": [
        "\u2265 4 points: PE likely (consider imaging).",
        "&lt; 4 points: PE unlikely (consider D-dimer first in low-risk patients).",
        "Use in conjunction with clinical judgement and local pathways.",
    ],
    "insert_options": [
        {
            "label": "Insert short Wells summary",
            "text": "Wells score \u22654 (PE likely) \u2013 imaging with CTPA appropriate based on clinical risk.",
        }
    ],
}

# Minimal static playbook for contextual helpers.
# Keys are (section, token).
#
# Section can be:
#   - a specific logical section (e.g. "indication", "observations", "conclusion"), or
#   - the special value "any" to indicate a wildcard helper that can be shown
#     in multiple sections (used via a fallback in build_smart_helper_cards).
SMART_HELPER_PLAYBOOK = {
    # Wells score helper: primarily anchored to Indication, but also available
    # as a generic helper in other sections via the ("any", "wells") key.
    ("indication", "wells"): [WELLS_PE_HELPER_CARD],
    ("any", "wells"): [WELLS_PE_HELPER_CARD],
    # Core-question-level toolkit for ?PE cases
    ("core_question", "pe"): [
        {
            "kind": "QUESTION_TOOLKIT",
            "title": "Tool bundle for ?PE (CTPA)",
            "summary": "Relevant tools for a case with suspected pulmonary embolism.",
            "bullets": [
                "CTPA imaging protocol.",
                "CTPA/PE report templates (admin + user).",
                "Checklist: RV/LV ratio, clot burden, alternative diagnoses.",
                "Right heart strain/severity notes.",
            ],
            "insert_options": [],
        }
    ],
}


def _normalise_selection_token(selection_text: str) -> str:
    """Normalise a text selection to a compact token used by the helper playbook."""
    if not selection_text:
        return ""
    text = selection_text.strip().lower()
    if "wells" in text:
        return "wells"
    if "pe" in text or "pulmonary embol" in text:
        return "pe"
    return ""



# ---- SmartHelperCard token splitting and matching helpers ----
def _split_card_tokens(raw_token: str):
    """
    Split a SmartHelperCard.token string into normalised tokens.

    Semantics for the token field:
    - Comma-separated list of variants (e.g. "sob, shortness of breath, wells score").
    - Case-insensitive.
    - Internal whitespace normalised to single spaces, e.g. "WELLS   score" -> "wells score".
    """
    if not raw_token:
        return []

    tokens = []
    for part in raw_token.split(","):
        canon = re.sub(r"\s+", " ", part.strip().lower())
        if canon:
            tokens.append(canon)
    return tokens

def _selection_matches_card(selection_text: str, raw_token: str) -> bool:
    """
    Decide whether a given SmartHelperCard (with a raw comma-separated token string)
    should match the current selection text.

    Rules:
    - If the card has no token (empty/NULL), treat it as a generic helper that always matches.
    - Otherwise, parse its token field into a list of normalised tokens.
    - Normalise the selection text (lowercase, collapse whitespace).
    - A card matches if ANY of its tokens appears as a contiguous substring in the
      normalised selection text, e.g.:
        - token "sob" matches "sob" or "SOB with chest pain".
        - token "wells score" only matches if "wells score" appears with the words adjacent.
    """
    tokens = _split_card_tokens(raw_token)
    # No explicit tokens means "generic" helper for the matching section/context.
    if not tokens:
        return True

    if not selection_text:
        return False

    selection_canon = re.sub(r"\s+", " ", selection_text.strip().lower())
    if not selection_canon:
        return False

    for tok in tokens:
        if tok in selection_canon:
            return True
    return False

# ---- DB-backed smart helper card builder ----
def _build_smart_helper_cards_from_db(context, selection_text: str, section: str):
    """Primary source for smart helper cards using SmartHelperCard.

    Matching strategy (updated):
    - Section filter: allow helpers whose section is either the specific section
      (e.g. INDICATION, OBSERVATIONS) or ANY.
    - Structural filters: if modality/body_part/module are present in context,
      prefer helpers that match them but also allow generic (NULL) helpers.
    - Token matching: All cards for the filtered section/context are loaded, and
      then Python logic applies flexible token matching (case-insensitive, comma-separated
      variants, multi-word tokens require adjacency) to the selection text.
    - If a card has no token, it always matches.

    Returns a list of dicts ready for JSON serialisation.
    """
    modality_enum = context.get("modality_enum")
    body_part_enum = context.get("body_part_enum")
    module_enum = context.get("module_enum")

    # Map the free-text section string to SmartHelperSectionEnum
    section_key = (section or "").strip().lower()
    section_enum = None
    if section_key == "indication":
        section_enum = SmartHelperSectionEnum.INDICATION
    elif section_key == "comparison":
        section_enum = SmartHelperSectionEnum.COMPARISON
    elif section_key == "technique":
        section_enum = SmartHelperSectionEnum.TECHNIQUE
    elif section_key == "observations":
        section_enum = SmartHelperSectionEnum.OBSERVATIONS
    elif section_key == "conclusion":
        section_enum = SmartHelperSectionEnum.CONCLUSION
    elif section_key == "recommendations":
        section_enum = SmartHelperSectionEnum.RECOMMENDATIONS

    # We always allow ANY plus the concrete section (if resolved)
    section_filters = [SmartHelperSectionEnum.ANY]
    if section_enum is not None:
        section_filters.append(section_enum)

    q = db.session.query(SmartHelperCard).filter(
        SmartHelperCard.is_active.is_(True),
        SmartHelperCard.section.in_(section_filters),
    )

    # Structural filters: match exact, or allow generic (NULL) helpers.
    if modality_enum is not None:
        q = q.filter(
            or_(
                SmartHelperCard.modality == modality_enum,
                SmartHelperCard.modality.is_(None),
            )
        )
    if body_part_enum is not None:
        q = q.filter(
            or_(
                SmartHelperCard.body_part == body_part_enum,
                SmartHelperCard.body_part.is_(None),
            )
        )
    if module_enum is not None:
        q = q.filter(
            or_(
                SmartHelperCard.module == module_enum,
                SmartHelperCard.module.is_(None),
            )
        )

    # Order by priority (higher first) then title for stability
    rows = (
        q.order_by(
            SmartHelperCard.priority.desc(),
            SmartHelperCard.title.asc(),
        )
        .limit(20)
        .all()
    )

    cards = []
    for row in rows:
        # Skip cards whose token list does not match the current selection text
        if not _selection_matches_card(selection_text, row.token or ""):
            continue
        # Convert enums to their value/name representation for JSON
        section_value = None
        if row.section is not None:
            section_value = (
                row.section.value
                if isinstance(row.section, SmartHelperSectionEnum)
                else str(row.section)
            )

        kind_value = None
        if row.kind is not None:
            kind_value = (
                row.kind.value
                if isinstance(row.kind, SmartHelperKindEnum)
                else str(row.kind)
            )

        card_obj = SimpleNamespace(
            id=row.id,
            title=row.title,
            summary=row.summary or "",
            kind=kind_value or "info",
            section=section_value,
            bullets=row.bullets_json or [],
            insert_options=row.insert_options_json or [],
            tags=row.tags or "",
            token=row.token,
            modality=row.modality,
            body_part=row.body_part,
            module=row.module,
            display_style=getattr(row, "display_style", "auto"),
            definition_json=(
                row.definition_json
                if isinstance(getattr(row, "definition_json", None), dict)
                else None
            ),
        )

        # Build unified bullet_sections and table_sections from definition_json
        bullet_sections = []
        table_sections = []

        if card_obj.definition_json:
            # Bullet groups
            groups = card_obj.definition_json.get("bullet_groups") or []
            for g in groups:
                items = g.get("items") or []
                if isinstance(items, list):
                    bullet_sections.append({
                        "title": g.get("title") or None,
                        "items": items,
                        "style": g.get("style") or "bullets",
                    })

            # Tables
            tables = card_obj.definition_json.get("tables") or []
            for t in tables:
                table_sections.append({
                    "title": t.get("title") or None,
                    "headers": t.get("headers") or [],
                    "rows": t.get("rows") or [],
                })

        # Fallback to legacy bullets_json if no modern bullets exist
        if not bullet_sections and card_obj.bullets:
            bullet_sections.append({
                "title": None,
                "items": card_obj.bullets,
                "style": "bullets",
            })

        # Serialize card
        vm = serialize_smart_helper_card(card_obj)

        # Inject new fields for frontend
        vm["bullet_sections"] = bullet_sections
        vm["table_sections"] = table_sections
        vm["insert_options"] = card_obj.insert_options or []

        # Add compatibility fields for frontend
        vm["kind"] = card_obj.kind
        vm["section"] = section_value
        vm["summary"] = vm.get("summary_html", "")
        vm["token"] = card_obj.token
        vm["modality"] = row.modality.name if row.modality is not None else None
        vm["body_part"] = row.body_part.name if row.body_part is not None else None
        vm["module"] = row.module.name if row.module is not None else None
        cards.append(vm)

    return cards

def build_smart_helper_cards(context, selection_text: str, section: str, user):
    """Build helper cards for contextual smart assistance.

    Phase 2c+ strategy:
    - Primary source: SmartHelperCard rows in the database, filtered by
      section, selection text, and structural context.
    - Fallback: static SMART_HELPER_PLAYBOOK for early bootstrap content
      (e.g. Wells score for PE) so the feature remains useful even with
      sparse DB content.
    """
    # Normalise selection text (may be an empty string if nothing is selected)
    selection_text = selection_text or ""

    # 1) Try database-backed smart helper cards first, using the raw selection text.
    #    Card tokens are matched in Python (case-insensitive, comma-separated variants,
    #    multi-word tokens requiring adjacency).
    db_cards = _build_smart_helper_cards_from_db(context, selection_text, section)
    if db_cards:
        return db_cards

    # 2) Fallback to the static playbook logic (existing behaviour) using the
    #    older normalised-token mapping (_normalise_selection_token) for
    #    bootstrap helpers such as Wells/PE.
    token = _normalise_selection_token(selection_text)
    if not token:
        return []

    section_key = (section or "").strip().lower() or "observations"

    cards = []

    # Exact (section, token) matches
    exact_cards = SMART_HELPER_PLAYBOOK.get((section_key, token), [])
    if exact_cards:
        for c in exact_cards:
            card_obj = SimpleNamespace(
                id=None,
                title=c.get("title"),
                summary=c.get("summary", ""),
                kind=c.get("kind", "info"),
                section=section_key,
                bullets=c.get("bullets", []),
                insert_options=c.get("insert_options", []),
                tags=c.get("tags", ""),
                token=c.get("token"),
                modality=None,
                body_part=None,
                module=None,
                display_style=c.get("display_style", "auto"),
            )
            vm = serialize_smart_helper_card(card_obj)
            vm["kind"] = card_obj.kind
            vm["section"] = card_obj.section
            vm["summary"] = vm.get("summary_html", "")
            vm["token"] = card_obj.token
            vm["modality"] = None
            vm["body_part"] = None
            vm["module"] = None
            cards.append(vm)

    # Wildcard helpers that apply to any section, e.g. ("any", "wells")
    any_cards = SMART_HELPER_PLAYBOOK.get(("any", token), [])
    if any_cards:
        for c in any_cards:
            card_obj = SimpleNamespace(
                id=None,
                title=c.get("title"),
                summary=c.get("summary", ""),
                kind=c.get("kind", "info"),
                section=section_key,
                bullets=c.get("bullets", []),
                insert_options=c.get("insert_options", []),
                tags=c.get("tags", ""),
                token=c.get("token"),
                modality=None,
                body_part=None,
                module=None,
                display_style=c.get("display_style", "auto"),
            )
            vm = serialize_smart_helper_card(card_obj)
            vm["kind"] = card_obj.kind
            vm["section"] = card_obj.section
            vm["summary"] = vm.get("summary_html", "")
            vm["token"] = card_obj.token
            vm["modality"] = None
            vm["body_part"] = None
            vm["module"] = None
            if vm not in cards:
                cards.append(vm)

    return cards

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
# Phase 2c: JSON endpoint for diagnosis suggestions
@main_bp.route("/case_workspace/suggest_diagnosis_phrases", methods=["GET", "POST"])
@login_required
def smart_diagnosis_suggestions_route():
    """
    JSON endpoint used by the Case Workspace diagnosis helper (Phase 2c+).

    Accepts structured case context and returns a list of candidate diagnosis
    labels drawn from user history, templates, and a static playbook. Later,
    optional AI helpers can be added as another tier in the same pipeline.
    """
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
    else:
        # For GET requests, treat query parameters as the payload so the endpoint
        # can be called without CSRF complications from the frontend.
        data = request.args.to_dict() if request.args else {}

    modality_name = (data.get("modality") or "").strip() or None
    body_part_name = (data.get("body_part") or "").strip() or None
    module_name = (data.get("module") or "").strip() or None

    indication = (data.get("indication") or "").strip()
    core_question = (data.get("core_question") or "").strip()
    current_diagnosis = (data.get("current_diagnosis") or "").strip()

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

    context = {
        "modality_enum": modality_enum,
        "body_part_enum": body_part_enum,
        "module_enum": module_enum,
        "indication": indication,
        "core_question": core_question,
        "current_diagnosis": current_diagnosis,
        "imaging_pattern": (data.get("imaging_pattern") or "").strip(),
        "ddx_shortlist": (data.get("ddx_shortlist") or "").strip(),
        "leading_diagnosis": (data.get("leading_diagnosis") or "").strip(),
        "supportive_findings": (data.get("supportive_findings") or "").strip(),
        "alt_considerations": (data.get("alt_considerations") or "").strip(),
        "red_flags": (data.get("red_flags") or "").strip(),
    }

    suggestions = build_smart_diagnosis_suggestions(context, current_user)

    return jsonify({"suggestions": suggestions})


# ---------------------------------------
@main_bp.route("/case_workspace/smart_helper", methods=["GET"])
@login_required
def smart_helper_route():
    """Generic smart helper endpoint for Case Workspace."""
    section = (request.args.get("section") or "").strip().lower()
    selection_text = (request.args.get("selection_text") or "").strip()

    modality_name = (request.args.get("modality") or "").strip() or None
    body_part_name = (request.args.get("body_part") or "").strip() or None
    module_name = (request.args.get("module") or "").strip() or None

    indication = (request.args.get("indication") or "").strip()
    core_question = (request.args.get("core_question") or "").strip()

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

    context = {
        "modality_enum": modality_enum,
        "body_part_enum": body_part_enum,
        "module_enum": module_enum,
        "indication": indication,
        "core_question": core_question,
    }

    cards = build_smart_helper_cards(context, selection_text, section, current_user)
    return jsonify({"cards": cards})


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
    file_path = os.path.jvoin(preview_folder, filename)

    if not os.path.exists(file_path):
        return abort(404)

    try:
        return send_file(file_path, as_attachment=False)
    except Exception:
        return abort(403)
    