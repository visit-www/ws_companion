# app/normal_measurement_views.py

from flask import Blueprint, render_template, request, jsonify, abort
from sqlalchemy import or_

from . import db
from .models import NormalMeasurement, BodyPartEnum, ModalityEnum

normal_measurements_bp = Blueprint(
    'normal_measurements',
    __name__,
    url_prefix='/measurements'
)

def _base_query():
    """Base query for active measurements."""
    return NormalMeasurement.query.filter_by(is_active=True)

@normal_measurements_bp.route('/')
def index():
    """
    Radiology Measurement Library index.
    Initial load: just the search UI (no results or small default set).
    Further results are loaded via JS from /measurements/api/search.
    """
    return render_template(
        'measurements/index.html',
        BodyPartEnum=BodyPartEnum,
        ModalityEnum=ModalityEnum
    )

@normal_measurements_bp.route('/<int:measurement_id>')
def detail(measurement_id):
    measurement = _base_query().get_or_404(measurement_id)
    return render_template(
        'measurements/detail.html',
        m=measurement
    )

@normal_measurements_bp.route('/api/search')
def api_search():
    """
    JSON endpoint for live search & autocomplete.

    Query params:
      - q: text
      - body_part: enum value (optional)
      - modality: enum value (optional)
      - diagnosis: text to search in tags (optional)
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

    query = _base_query()

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

    def serialize(m: NormalMeasurement):
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
            "url": f"/measurements/{m.id}",
        }

    return jsonify({
        "results": [serialize(m) for m in results]
    })