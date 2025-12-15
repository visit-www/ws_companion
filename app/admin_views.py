from flask_admin.contrib.sqla import ModelView
from flask_admin import expose
from flask_admin.form import FileUploadField
from flask import redirect, url_for, flash, request
from flask_login import current_user
from wtforms_sqlalchemy.fields import QuerySelectField
from wtforms import SelectField
from werkzeug.utils import secure_filename
import os
import shutil
import json
from datetime import datetime, timezone
from sqlalchemy import inspect, or_
import re

from . import db
from .models import (
    Content,
    Reference,
    User,
    NormalMeasurement,
    BodyPartEnum,
    ModalityEnum,
    AdminReportTemplate,
    ImagingProtocol,
    ClassificationSystem,
    SmartHelperCard,
    SmartHelperSectionEnum,
    SmartHelperKindEnum,
)
from config import ANONYMOUS_USER_ID, userdir

# For SmartHelperCard preview serialization
from .util import serialize_smart_helper_card

# ExtendModelView class for general model handling
class ExtendModelView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False

    @property
    def column_list(self):
        return self.scaffold_list_columns() + ['user_id', 'username']

from flask_admin.contrib.sqla import ModelView
from flask_admin.form import FileUploadField
from werkzeug.utils import secure_filename
from flask import flash, redirect, url_for
from flask_login import current_user
import os
import shutil
from datetime import datetime, timezone
from . import db

class MyModelView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False
    form_excluded_columns = ['filepath']
    form_overrides = {'file': FileUploadField}
    form_args = {
        'file': {
            'label': 'Select File',
            'base_path': os.path.join('dummy_folder'),
            'allow_overwrite': False,
            'allowed_extensions': [
                'txt', 'pdf', 'pptx', 'ppt', 'doc', 'xls', 'docx', 'png', 'jpg', 'jpeg', 'xlsx', 
                'html', 'md', 'mmd', 'svg', 'drawio', 'webp'
            ],
        }
    }

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        flash('Admin access required.', 'warning')
        return redirect(url_for('app_user.login'))

    def custom_upload_file(self, form, model):
        category = model.category.value if hasattr(model.category, 'value') else model.category
        module = model.module.value if hasattr(model.module, 'value') else model.module
        filename = secure_filename(form.file.data.filename)
        uploaded_file = os.path.join('dummy_folder', filename)
        target_folder = os.path.join('files', category, module)
        os.makedirs(target_folder, exist_ok=True)
        shutil.move(uploaded_file, target_folder)
        model.filepath = os.path.join(target_folder, filename)

    def custom_delete_file(self, model):
        trash_folder = 'trash'
        date_folder = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        current_date_folder = os.path.join(trash_folder, date_folder)
        os.makedirs(current_date_folder, exist_ok=True)

        if model.filepath and os.path.exists(model.filepath):
            try:
                shutil.move(model.filepath, current_date_folder)
                model.filepath = None
                model.file = None
            except OSError as e:
                flash(f'Error deleting file: {str(e)}', 'danger')

    def on_model_change(self, form, model, is_created):
        upload_file = bool(form.file.data)
        old_category = model.category if not is_created else None
        old_module = model.module if not is_created else None
        original_filepath = model.filepath  # Store the original file path for reference

        try:
            # Check if a new file is being uploaded on creation
            if is_created and upload_file:
                self.custom_upload_file(form, model)
            else:
                # If the category or module has changed, move the file to the new directory
                if not is_created and (old_category != model.category or old_module != model.module) and original_filepath:
                    # Determine the new directory based on updated category and module
                    new_category = model.category.value if hasattr(model.category, 'value') else model.category
                    new_module = model.module.value if hasattr(model.module, 'value') else model.module
                    new_folder = os.path.join('files', new_category, new_module)
                    os.makedirs(new_folder, exist_ok=True)

                    # Move the file to the new folder
                    filename = os.path.basename(original_filepath)
                    new_filepath = os.path.join(new_folder, filename)
                    shutil.move(original_filepath, new_filepath)
                    model.filepath = new_filepath  # Update the model's filepath

                    flash(f"File moved to the new category/module folder: {new_category}/{new_module}", 'success')

            db.session.add(model)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred during the update: {e}", 'danger')

    def on_model_delete(self, model):
        self.custom_delete_file(model)
        db.session.delete(model)
        db.session.commit()



# Custom User Model View for handling specific user-related admin tasks
class UserModelView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False

    form_widget_args = {
        "ai_calls_used_today": {"readonly": True},
        "ai_calls_last_reset": {"readonly": True},
    }

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        flash('Admin access required.', 'warning')
        return redirect(url_for('app_user.login'))

    def serialize_model(self, instance):
        return {c.key: getattr(instance, c.key) for c in inspect(instance).mapper.column_attrs}

    def custom_user_delete(self, model):
        if isinstance(model, User):
            user_id = model.id
            if user_id == ANONYMOUS_USER_ID or model.username == 'admin':
                flash("Deleting the anonymous user or admin is restricted.", "warning")
                return

            # Archive metadata and delete user files
            user_metadata = {
                "user": self.serialize_model(model),
                "profile": self.serialize_model(model.profile) if model.profile else None,
            }
            metadata_file_path = os.path.join('archived', f"user_{user_id}_metadata.json")
            os.makedirs(os.path.dirname(metadata_file_path), exist_ok=True)
            with open(metadata_file_path, 'w') as f:
                json.dump(user_metadata, f, indent=4, default=str)

            user_dir = os.path.join(userdir, f"{user_id}")
            if os.path.exists(user_dir):
                shutil.rmtree(user_dir)

    def on_model_delete(self, model):
        self.custom_user_delete(model)
        db.session.delete(model)
        db.session.commit()


class ReferenceAdmin(ModelView):
    # Define form columns to include content title instead of content_id
    form_columns = ['title', 'category', 'module', 'content_id', 'file', 'filepath', 'url', 'embed_code', 'description']

    # Override form fields
    form_overrides = {
        'content_id': QuerySelectField,  # Display Content titles in dropdown
        'file': FileUploadField
    }
    form_args = {
        'content_id': {
            'query_factory': lambda: db.session.query(Content),  # Query Content model for dropdown
            'get_label': 'title'  # Show Content title in dropdown instead of ID
        },
        'file': {
            'label': 'Select File',
            'base_path': os.path.join('dummy_folder'),  # Adjust to the correct folder path for uploads
            'allow_overwrite': False,
            'allowed_extensions': [
                'txt', 'pdf', 'pptx', 'ppt', 'doc', 'xls', 'docx', 'png', 'jpg', 'jpeg', 'xlsx', 
                'html', 'md', 'mmd', 'svg', 'drawio', 'webp'
            ],
        }
    }

    # Custom column list for easy viewing
    column_list = ('title', 'category', 'module', 'content_id')
    column_labels = {'content_id': 'Select Content title'}

    # Custom file upload handler
    def custom_upload_file(self, form, model):
        category = model.category.value if hasattr(model.category, 'value') else model.category
        module = model.module.value if hasattr(model.module, 'value') else model.module
        filename = secure_filename(form.file.data.filename)
        uploaded_file = os.path.join('dummy_folder', filename)
        target_folder = os.path.join('files', category, module)
        os.makedirs(target_folder, exist_ok=True)
        shutil.move(uploaded_file, target_folder)
        model.filepath = os.path.join(target_folder, filename)

    # Handle file deletion by moving files to a trash folder
    def custom_delete_file(self, model):
        trash_folder = 'trash'
        date_folder = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        current_date_folder = os.path.join(trash_folder, date_folder)
        os.makedirs(current_date_folder, exist_ok=True)

        if model.filepath and os.path.exists(model.filepath):
            try:
                shutil.move(model.filepath, current_date_folder)
                model.filepath = None
                model.file = None
            except OSError as e:
                flash(f'Error deleting file: {str(e)}', 'danger')

    # Override on_model_change to set content_id based on content_title selection
    def on_model_change(self, form, model, is_created):
        # Set content_id based on the selected content_title
        if form.content_id.data:
            selected_content = form.content_id.data
            model.content_id = selected_content.id

        # Handle file upload if file data is provided
        if form.file.data:
            self.custom_upload_file(form, model)

        db.session.add(model)
        db.session.commit()

    # Override on_model_delete to handle file deletion on model delete
    def on_model_delete(self, model):
        self.custom_delete_file(model)  # Delete file if model is deleted
        db.session.delete(model)
        db.session.commit()
        
from wtforms import StringField, TextAreaField, SelectField, FieldList, FormField, Form
from flask_admin.form import rules
import json

class ImagingProtocolAdmin(ExtendModelView):
    """
    Custom admin for ImagingProtocol that hides raw JSON
    and exposes human-friendly fields.
    """

    # Don’t show parameters_json directly in the form
    form_excluded_columns = ('parameters_json',)

    # You can also hide audit fields here if needed:
    # form_excluded_columns = ('parameters_json', 'created_at', 'updated_at', ...)

    # Extra form fields shown to the user
    form_extra_fields = {
        'scanner': StringField('Scanner / scanner notes'),
        'patient_position': StringField('Patient position'),
        'contrast_block': TextAreaField(
            'Contrast (type | volume_ml | rate_ml_s | saline_ml | timing)',
            description="Example: Non-ionic iodinated | 80 | 4 | 30 | Trigger in main PA at 120 HU"
        ),
        'phases_block': TextAreaField(
            'CT Phases (one per line: name | kVp | mAs | slice_mm | interval_mm | notes)',
            description="Example:\n"
                        "Non-contrast | 120 | 200–250 | 3 | 3 | Optional\n"
                        "PE phase | 100 | 200–250 | 1 | 0.8 | Lung apices to below CP angles"
        ),
        'sequences_block': TextAreaField(
            'MRI Sequences (plane | name | slice_mm | gap_mm | fat_sat | breath_hold | notes | phase_group)',
            description=(
                "Example:\n"
                "Coronal | T2 SSFSE | 5 | 0 | FS | BH | Whole abdomen and pelvis | pre\n"
                "Coronal | T1 3D GRE arterial | 3 | 0 | DIXON | BH | 20–30 s post injection | post"
            )
        ),
    }

    form_args = {
        'indication': {
            'description': (
                "Free-text clinical indications. Best to keep this as simple text, "
                "but you may use inline HTML tags for emphasis:&lt;strong&gt;…&lt;/strong&gt; (makes text <strong>bold</strong>),	&lt;i&gt;…&lt;/i&gt; (makes text <i>italic</i>),&lt;u&gt;…&lt;/u&gt; (makes text <u>underlined</u>),&lt;mark&gt;…&lt;/mark&gt; (makkes text<mark>highlighted</mark>)"
                "Full HTML is also supported if needed."
            )
        },
        'contrast_details': {
            'description': (
                "Free-text contrast notes (e.g. eGFR guidance, allergy precautions, when to "
                "avoid contrast). Prefer simple text with optional inline HTML tags for emphasis:&lt;strong&gt;…&lt;/strong&gt; (makes text <strong>bold</strong>),	&lt;i&gt;…&lt;/i&gt; (makes text <i>italic</i>),&lt;u&gt;…&lt;/u&gt; (makes text <u>underlined</u>),&lt;mark&gt;…&lt;/mark&gt; (makkes text<mark>highlighted</mark>)"
                "Full HTML is supported if you want richer layout."
            )
        },
        'technique_text': {
            'description': (
                "Detailed technique description. You can use simple paragraphs or enhance with "
                "inline HTML tags for emphasis:&lt;strong&gt;…&lt;/strong&gt; (makes text <strong>bold</strong>),	&lt;i&gt;…&lt;/i&gt; (makes text <i>italic</i>),&lt;u&gt;…&lt;/u&gt; (makes text <u>underlined</u>),&lt;mark&gt;…&lt;/mark&gt; (makkes text<mark>highlighted</mark>). Full HTML is also allowed, but best practice is clear text with occasional "
                "inline tags rather than very complex markup."
            )
        }
    }

    # Optional: make form layout nicer
    form_create_rules = form_edit_rules = [
        'name',
        'modality',
        'body_part',
        'module',
        'indication',
        'is_emergency',
        'uses_contrast',
        'contrast_details',
        rules.FieldSet(('scanner', 'patient_position'), 'Scanner / Position'),
        'contrast_block',
        'technique_text',
        'phases_block',
        'sequences_block',
        'tags',
    ]

    def _parse_block(self, block_text, expected_parts):
        """
        Parse a multi-line textarea where each line is 'a | b | c | ...'
        Returns a list of dicts.
        """
        items = []
        if not block_text:
            return items

        for raw_line in block_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split('|')]
            # pad parts to expected length
            if len(parts) < expected_parts:
                parts += [None] * (expected_parts - len(parts))
            items.append(parts[:expected_parts])
        return items

    def on_model_change(self, form, model, is_created):
        """
        Called when a form is submitted. Build parameters_json
        from the helper fields before saving.
        """
        params = {}

        # Simple scalars
        if form.scanner.data:
            params['scanner'] = form.scanner.data
        if form.patient_position.data:
            params['patient_position'] = form.patient_position.data

        # Contrast
        contrast_items = self._parse_block(form.contrast_block.data, 5)
        if contrast_items:
            t, vol, rate, saline, timing = contrast_items[0]
            params['contrast'] = {
                'type': t,
                'volume_ml': vol,
                'rate_ml_s': rate,
                'saline_chaser_ml': saline,
                'timing': timing,
            }

        # CT phases
        phase_rows = self._parse_block(form.phases_block.data, 6)
        if phase_rows:
            params['phases'] = []
            for name, kvp, mas, slice_mm, interval_mm, notes in phase_rows:
                params['phases'].append({
                    'name': name,
                    'kVp': kvp,
                    'mAs': mas,
                    'slice_thickness_mm': slice_mm,
                    'interval_mm': interval_mm,
                    'notes': notes,
                })

        # MRI sequences
        seq_rows = self._parse_block(form.sequences_block.data, 8)
        if seq_rows:
            params['sequences'] = []
            
            for row in seq_rows:
                plane, name, slice_mm, gap_mm, fat_sat, breath_hold, notes, phase_group = row[:8]
                params['sequences'].append({
                    'plane': plane,
                    'name': name,
                    'slice_thickness_mm': slice_mm,
                    'gap_mm': gap_mm,
                    'fat_sat':fat_sat,
                    'breath_hold':breath_hold,
                    'notes': notes,
                    'phase_group': (phase_group or '').lower() or 'pre',
                })

        # Attach to model as JSON
        model.parameters_json = params or None

        # Proceed with normal save
        return super().on_model_change(form, model, is_created)

    def on_form_prefill(self, form, id):
        """
        Flask-Admin passes `id` here, not the model.
        We need to fetch the model ourselves.
        """
        model = self.get_one(id)
        if not model:
            # nothing to prefill
            return

        params = model.parameters_json or {}

        # Example fields – adapt to your actual helper fields
        form.scanner.data = params.get('scanner', '')
        form.patient_position.data = params.get('patient_position', '')

        # Contrast
        contrast = params.get('contrast')
        if contrast:
            form.contrast_block.data = " | ".join([
                contrast.get('type', '') or '',
                str(contrast.get('volume_ml', '') or ''),
                str(contrast.get('rate_ml_s', '') or ''),
                str(contrast.get('saline_chaser_ml', '') or ''),
                contrast.get('timing', '') or '',
            ])

        # Phases (for CT)
        phases = params.get('phases') or []
        if phases:
            lines = []
            for ph in phases:
                line = " | ".join([
                    ph.get('name', '') or '',
                    str(ph.get('kVp', '') or ''),
                    str(ph.get('mAs', '') or ''),
                    str(ph.get('slice_thickness_mm', '') or ''),
                    str(ph.get('interval_mm', '') or ''),
                    ph.get('notes', '') or '',
                ])
                lines.append(line)
            form.phases_block.data = "\n".join(lines)

        # Sequences (for MRI)
        seqs = params.get('sequences') or []
        if seqs:
            lines = []
            for s in seqs:
                line = " | ".join([
                    s.get('plane', '') or '',
                    s.get('name', '') or '',
                    str(s.get('slice_thickness_mm', '') or ''),
                    str(s.get('gap_mm', '') or ''),
                    s.get('fat_sat', '') or '',
                    s.get('breath_hold', '') or '',
                    s.get('notes', '') or '',
                    s.get('phase_group', '') or '',
                ])
                lines.append(line)
            form.sequences_block.data = "\n".join(lines)

        # Let the parent do any default prefill work as well (optional)
        return super().on_form_prefill(form, id)
# *-------------------------------------------------------------------------------------
# normal measurments admin views:

# -------------------------------------------------------------------------------------
# AdminReportTemplate custom admin view
class AdminReportTemplateAdmin(ExtendModelView):
    """
    Custom admin for AdminReportTemplate that hides raw JSON and exposes
    friendly fields for indication/clinical history and observations.
    """

    # Do not show raw JSON, file upload, or audit fields directly
    form_excluded_columns = (
        "definition_json",
        "created_at",
        "updated_at",
        "user_report_templates",
        "file",
        "filepath",
        "description",
        "category",
        "created_by_user_id",
        "usage_count",
    )

    # Extra helper fields, more guided and with conclusions/recommendations, plus advanced JSON
    form_extra_fields = {
        "raw_sections_json": TextAreaField(
            "Advanced: full JSON for sections",
            description=(
                "If you already have the full JSON for all sections (as a list or as "
                '{"sections": [...]}), paste it here.\n'
                "IMPORTANT:\n"
                "- When this field is non-empty and valid JSON, it will be used to build the "
                "template sections and the individual fields below (Indication, Clinical history, "
                "Core question, Comparison, Technique, Observations, Conclusions, "
                "Recommendations) will be ignored/overwritten for this save.\n"
                "- Leave this empty if you prefer to build the template using the section fields below."
            ),
        ),
        "indication_block": TextAreaField(
            "Indication/Clinical history",
            description=(
                "Step 1 – What is the indication for the scan?\n"
                "- Easiest: type plain text, e.g. \"?Pulmonary embolism\".\n"
                "- You can also use inline HTML for emphasis if needed."
            ),
        ),
        "core_question_block": TextAreaField(
            "Core question",
            description=(
                "Step 3 – What is the key clinical question?\n"
                "Example: \"Is there CT evidence of acute PE and any signs of right heart strain?\".\n"
                "You can also use JSON if you want multiple core questions."
            ),
        ),
        "comparison_block": TextAreaField(
            "Comparison",
            description=(
                "Step 4 – Comparison with prior imaging.\n"
                "- Plain text: e.g. \"No relevant prior imaging available for comparison.\".\n"
                "- Or include placeholders in square brackets to force editing, e.g.:\n"
                "  \"Compared with CT chest dated [dd/mm/yyyy].\""
            ),
        ),
        "technique_block": TextAreaField(
            "Technique",
            description=(
                "Step 5 – Technique description (how the study was acquired).\n"
                "- This can often be auto-prefilled from the Imaging Protocol.\n"
                "- You can edit it here as the default technique text for this template."
            ),
        ),
        "observations_block": TextAreaField(
            "Observations / Findings",
            description=(
                "Step 6 – Key imaging observations.\n"
                "- Plain text or HTML → one combined observations section.\n"
                "- JSON → multiple subsections (e.g. pulmonary arteries, RV strain, lung parenchyma).\n"
                "Example JSON:\n"
                "[\n"
                "  {\"id\": \"pe_findings\", \"label\": \"Pulmonary arteries\", \"text\": \"Filling defects in...\"},\n"
                "  {\"id\": \"rv_strain\", \"label\": \"Right heart / RV strain\", \"text\": \"RV:LV > 1, septal bowing...\"}\n"
                "]"
            ),
        ),
        "conclusions_block": TextAreaField(
            "Conclusion / Impression",
            description=(
                "Step 7 – Your overall impression in radiologist language.\n"
                "- Typically 2–5 numbered lines summarising the diagnosis and severity.\n"
                "- You can also use JSON to define multiple impression subsections if needed."
            ),
        ),
        "recommendations_block": TextAreaField(
            "Recommendations",
            description=(
                "Step 8 – Actionable recommendations for the referrer.\n"
                "- Plain text (e.g. anticoagulate, consider echo, follow-up imaging).\n"
                "- Or JSON if you want structured recommendation subsections."
            ),
        ),
    }

    # Define a clinically logical field order for the form, with advanced JSON field above helpers
    form_create_rules = form_edit_rules = [
        "template_name",
        "modality",
        "body_part",
        "module",
        "tags",
        "template_type",
        "is_active",
        "raw_sections_json",
        rules.FieldSet(("indication_block",), "Indication/Clinical history"),
        rules.FieldSet(("core_question_block",), "Core question"),
        rules.FieldSet(("comparison_block",), "Comparison"),
        rules.FieldSet(("technique_block",), "Technique"),
        rules.FieldSet(("observations_block",), "Observations / Findings"),
        rules.FieldSet(("conclusions_block",), "Conclusion / Impression"),
        rules.FieldSet(("recommendations_block",), "Recommendations"),
    ]

    def _parse_sections_block(self, raw_value, default_section_id, default_label, default_order, default_export_targets):
        """
        Parse a textarea that may contain JSON or plain text.

        - If JSON (list or {\"sections\": [...]}) is detected, convert each item into a section dict.
        - Otherwise, treat the whole value as a single section.
        """
        sections = []
        raw_value = (raw_value or "").strip()
        if not raw_value:
            return sections

        # Try JSON first
        if raw_value.startswith("{") or raw_value.startswith("["):
            try:
                parsed = json.loads(raw_value)
                if isinstance(parsed, dict):
                    parsed_list = parsed.get("sections", [])
                else:
                    parsed_list = parsed

                for idx, item in enumerate(parsed_list):
                    if not isinstance(item, dict):
                        continue
                    text = item.get("text") or item.get("default_text") or ""
                    if not text:
                        continue
                    sec_id = item.get("id") or f"{default_section_id}_{idx+1}"
                    label = item.get("label") or f"{default_label} {idx+1}"
                    order = item.get("order") or default_order + idx
                    rich = bool(item.get("rich", True))
                    export_targets = item.get("export_targets", default_export_targets)

                    sections.append(
                        {
                            "id": sec_id,
                            "label": label,
                            "order": order,
                            "type": "textarea",
                            "default_text": text,
                            "rich": rich,
                            "export_targets": export_targets,
                        }
                    )
                return sections
            except Exception:
                # Fall back to treating as plain text if JSON parsing fails
                pass

        # Plain text / HTML: single section
        is_rich = "<" in raw_value and ">" in raw_value
        sections.append(
            {
                "id": default_section_id,
                "label": default_label,
                "order": default_order,
                "type": "textarea",
                "default_text": raw_value,
                "rich": is_rich,
                "export_targets": default_export_targets,
            }
        )
        return sections

    def on_model_change(self, form, model, is_created):
        """
        Build or update definition_json from the helper fields, or from advanced JSON if provided.
        """
        # Start from existing definition if any
        definition = model.definition_json or {}
        sections = definition.get("sections", []) or []

        # Remove any previously generated indication, clinical history, core question, comparison, technique, observation, conclusion, or recommendation sections
        indication_prefixes = ("indication", "indication_history")
        clinical_history_prefixes = ("clinical_history",)
        core_question_prefixes = ("core_question", "question")
        comparison_prefixes = ("comparison",)
        technique_prefixes = ("technique",)
        observation_prefixes = ("observations", "findings", "pe_", "rv_", "lung_", "other_findings")
        conclusion_prefixes = ("conclusion", "impression")
        recommendation_prefixes = ("recommendation", "follow_up", "management")

        filtered_sections = []
        for s in sections:
            sid = s.get("id", "")
            if (
                sid.startswith(indication_prefixes)
                or sid.startswith(clinical_history_prefixes)
                or sid.startswith(core_question_prefixes)
                or sid.startswith(comparison_prefixes)
                or sid.startswith(technique_prefixes)
                or sid.startswith(observation_prefixes)
                or sid.startswith(conclusion_prefixes)
                or sid.startswith(recommendation_prefixes)
            ):
                continue
            filtered_sections.append(s)

        # If advanced JSON field is used, treat it as authoritative for sections
        raw_json = None
        if hasattr(form, "raw_sections_json") and form.raw_sections_json.data:
            candidate = (form.raw_sections_json.data or "").strip()
            if candidate:
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict):
                        parsed_sections = parsed.get("sections", [])
                    else:
                        parsed_sections = parsed

                    # Only accept if it's a list of dict-like items
                    if isinstance(parsed_sections, list):
                        cleaned = []
                        for item in parsed_sections:
                            if isinstance(item, dict) and item.get("id") and item.get("default_text", item.get("text")):
                                # Normalise: if 'text' exists but 'default_text' missing, promote it
                                if "default_text" not in item and "text" in item:
                                    item = dict(item)
                                    item["default_text"] = item["text"]
                                cleaned.append(item)
                        raw_json = cleaned
                except Exception:
                    # If JSON is invalid, ignore this field and fall back to helper blocks
                    flash(
                        "Could not parse full sections JSON. Falling back to the individual section fields.",
                        "warning",
                    )

        if raw_json is not None:
            # Preserve non-section metadata, but override sections with the JSON list
            definition["version"] = definition.get("version", 1)
            definition["meta"] = definition.get("meta", {})
            if hasattr(model, "modality") and model.modality is not None:
                definition["meta"]["modality"] = getattr(model.modality, "value", str(model.modality))
            if hasattr(model, "body_part") and model.body_part is not None:
                definition["meta"]["body_part"] = getattr(model.body_part, "value", str(model.body_part))
            definition["meta"]["template_purpose"] = model.template_name

            # Combine preserved non-generated sections with the JSON provided ones
            definition["sections"] = filtered_sections + raw_json
            model.definition_json = definition or None
            return super().on_model_change(form, model, is_created)

        # Rebuild from helper fields (only if they contain data)
        new_sections = []

        if hasattr(form, "indication_block") and form.indication_block.data:
            new_sections.extend(
                self._parse_sections_block(
                    form.indication_block.data,
                    default_section_id="indication",
                    default_label="Indication/Clinical history",
                    default_order=10,
                    default_export_targets=[
                        "smart_report.clinical_info",
                        "case_workspace.clinical_info",
                    ],
                )
            )


        if hasattr(form, "core_question_block") and form.core_question_block.data:
            new_sections.extend(
                self._parse_sections_block(
                    form.core_question_block.data,
                    default_section_id="core_question",
                    default_label="Core question",
                    default_order=20,
                    default_export_targets=[
                        "smart_report.core_question",
                        "case_workspace.core_question",
                    ],
                )
            )

        if hasattr(form, "comparison_block") and form.comparison_block.data:
            new_sections.extend(
                self._parse_sections_block(
                    form.comparison_block.data,
                    default_section_id="comparison",
                    default_label="Comparison",
                    default_order=30,
                    default_export_targets=[
                        "smart_report.comparison",
                        "case_workspace.comparison",
                    ],
                )
            )

        if hasattr(form, "technique_block") and form.technique_block.data:
            new_sections.extend(
                self._parse_sections_block(
                    form.technique_block.data,
                    default_section_id="technique",
                    default_label="Technique",
                    default_order=40,
                    default_export_targets=[
                        "smart_report.technique",
                        "case_workspace.technique",
                    ],
                )
            )

        if hasattr(form, "observations_block") and form.observations_block.data:
            new_sections.extend(
                self._parse_sections_block(
                    form.observations_block.data,
                    default_section_id="observations",
                    default_label="Observations",
                    default_order=50,
                    default_export_targets=[
                        "smart_report.observations",
                        "case_workspace.observations",
                    ],
                )
            )

        if hasattr(form, "conclusions_block") and form.conclusions_block.data:
            new_sections.extend(
                self._parse_sections_block(
                    form.conclusions_block.data,
                    default_section_id="conclusion",
                    default_label="Conclusion / Impression",
                    default_order=80,
                    default_export_targets=[
                        "smart_report.conclusions",
                        "case_workspace.impression",
                    ],
                )
            )

        if hasattr(form, "recommendations_block") and form.recommendations_block.data:
            new_sections.extend(
                self._parse_sections_block(
                    form.recommendations_block.data,
                    default_section_id="recommendations",
                    default_label="Recommendations",
                    default_order=90,
                    default_export_targets=[
                        "smart_report.recommendations",
                        "case_workspace.recommendations",
                    ],
                )
            )

        # Combine preserved sections with newly generated ones
        definition["version"] = definition.get("version", 1)
        definition["meta"] = definition.get("meta", {})
        # Optionally sync basic meta from model
        if hasattr(model, "modality") and model.modality is not None:
            definition["meta"]["modality"] = getattr(model.modality, "value", str(model.modality))
        if hasattr(model, "body_part") and model.body_part is not None:
            definition["meta"]["body_part"] = getattr(model.body_part, "value", str(model.body_part))
        definition["meta"]["template_purpose"] = model.template_name

        definition["sections"] = filtered_sections + new_sections

        model.definition_json = definition or None

        # Proceed with normal save
        return super().on_model_change(form, model, is_created)

    def on_form_prefill(self, form, id):
        """
        Populate helper fields from definition_json when editing an existing template.
        """
        model = self.get_one(id)
        if not model:
            return

        definition = model.definition_json or {}
        sections = definition.get("sections", []) or []

        # Gather current sections by clinical grouping
        indication_sections = []
        clinical_history_sections = []
        core_question_sections = []
        comparison_sections = []
        technique_sections = []
        observation_sections = []
        conclusion_sections = []
        recommendation_sections = []

        indication_prefixes = ("indication", "indication_history")
        clinical_history_prefixes = ("clinical_history",)
        core_question_prefixes = ("core_question", "question")
        comparison_prefixes = ("comparison",)
        technique_prefixes = ("technique",)
        observation_prefixes = ("observations", "findings", "pe_", "rv_", "lung_", "other_findings")
        conclusion_prefixes = ("conclusion", "impression")
        recommendation_prefixes = ("recommendation", "follow_up", "management")

        for s in sections:
            sid = s.get("id", "")
            if sid.startswith(indication_prefixes):
                indication_sections.append(s)
            elif sid.startswith(clinical_history_prefixes):
                clinical_history_sections.append(s)
            elif sid.startswith(core_question_prefixes):
                core_question_sections.append(s)
            elif sid.startswith(comparison_prefixes):
                comparison_sections.append(s)
            elif sid.startswith(technique_prefixes):
                technique_sections.append(s)
            elif sid.startswith(observation_prefixes):
                observation_sections.append(s)
            elif sid.startswith(conclusion_prefixes):
                conclusion_sections.append(s)
            elif sid.startswith(recommendation_prefixes):
                recommendation_sections.append(s)

        # Prefill indication_block as JSON if multiple sections exist, otherwise as plain text
        if indication_sections:
            if len(indication_sections) == 1:
                # Single section: show just the text for easy editing
                form.indication_block.data = indication_sections[0].get("default_text", "")
            else:
                # Multiple sections: show a JSON list
                items = []
                for s in indication_sections:
                    items.append(
                        {
                            "id": s.get("id"),
                            "label": s.get("label"),
                            "text": s.get("default_text", ""),
                            "export_targets": s.get("export_targets", []),
                            "order": s.get("order"),
                            "rich": s.get("rich", True),
                        }
                    )
                form.indication_block.data = json.dumps(items, indent=2)

        # Prefill clinical_history_block
        if clinical_history_sections:
            if len(clinical_history_sections) == 1:
                form.clinical_history_block.data = clinical_history_sections[0].get("default_text", "")
            else:
                items = []
                for s in clinical_history_sections:
                    items.append(
                        {
                            "id": s.get("id"),
                            "label": s.get("label"),
                            "text": s.get("default_text", ""),
                            "export_targets": s.get("export_targets", []),
                            "order": s.get("order"),
                            "rich": s.get("rich", True),
                        }
                    )
                form.clinical_history_block.data = json.dumps(items, indent=2)

        # Prefill core_question_block
        if core_question_sections:
            if len(core_question_sections) == 1:
                form.core_question_block.data = core_question_sections[0].get("default_text", "")
            else:
                items = []
                for s in core_question_sections:
                    items.append(
                        {
                            "id": s.get("id"),
                            "label": s.get("label"),
                            "text": s.get("default_text", ""),
                            "export_targets": s.get("export_targets", []),
                            "order": s.get("order"),
                            "rich": s.get("rich", True),
                        }
                    )
                form.core_question_block.data = json.dumps(items, indent=2)

        # Prefill observations_block similarly
        if observation_sections:
            if len(observation_sections) == 1:
                form.observations_block.data = observation_sections[0].get("default_text", "")
            else:
                items = []
                for s in observation_sections:
                    items.append(
                        {
                            "id": s.get("id"),
                            "label": s.get("label"),
                            "text": s.get("default_text", ""),
                            "export_targets": s.get("export_targets", []),
                            "order": s.get("order"),
                            "rich": s.get("rich", True),
                        }
                    )
                form.observations_block.data = json.dumps(items, indent=2)

        # Prefill comparison_block
        if comparison_sections:
            if len(comparison_sections) == 1:
                form.comparison_block.data = comparison_sections[0].get("default_text", "")
            else:
                items = []
                for s in comparison_sections:
                    items.append(
                        {
                            "id": s.get("id"),
                            "label": s.get("label"),
                            "text": s.get("default_text", ""),
                            "export_targets": s.get("export_targets", []),
                            "order": s.get("order"),
                            "rich": s.get("rich", True),
                        }
                    )
                form.comparison_block.data = json.dumps(items, indent=2)
        else:
            # Default comparison text if nothing exists yet
            if hasattr(form, "comparison_block") and not form.comparison_block.data:
                form.comparison_block.data = (
                    "No relevant prior imaging available for comparison.\n"
                    "Compared with [modality / study type] dated [dd/mm/yyyy] (if applicable)."
                )

        # Prefill technique_block
        if technique_sections:
            if len(technique_sections) == 1:
                form.technique_block.data = technique_sections[0].get("default_text", "")
            else:
                items = []
                for s in technique_sections:
                    items.append(
                        {
                            "id": s.get("id"),
                            "label": s.get("label"),
                            "text": s.get("default_text", ""),
                            "export_targets": s.get("export_targets", []),
                            "order": s.get("order"),
                            "rich": s.get("rich", True),
                        }
                    )
                form.technique_block.data = json.dumps(items, indent=2)
        else:
            # Try to prefill technique from ImagingProtocol if available and if form is empty
            if hasattr(form, "technique_block") and not form.technique_block.data:
                try:
                    # Match on modality/body_part if these exist on the model
                    q = db.session.query(ImagingProtocol)
                    if hasattr(model, "modality") and model.modality is not None:
                        q = q.filter(ImagingProtocol.modality == model.modality)
                    if hasattr(model, "body_part") and model.body_part is not None:
                        q = q.filter(ImagingProtocol.body_part == model.body_part)
                    protocol = q.first()
                    if protocol and getattr(protocol, "technique_text", None):
                        form.technique_block.data = protocol.technique_text
                except Exception:
                    # Fail silently if no protocol available
                    pass

        # Prefill conclusions_block
        if conclusion_sections:
            if len(conclusion_sections) == 1:
                form.conclusions_block.data = conclusion_sections[0].get("default_text", "")
            else:
                items = []
                for s in conclusion_sections:
                    items.append(
                        {
                            "id": s.get("id"),
                            "label": s.get("label"),
                            "text": s.get("default_text", ""),
                            "export_targets": s.get("export_targets", []),
                            "order": s.get("order"),
                            "rich": s.get("rich", True),
                        }
                    )
                form.conclusions_block.data = json.dumps(items, indent=2)

        # Prefill recommendations_block
        if recommendation_sections:
            if len(recommendation_sections) == 1:
                form.recommendations_block.data = recommendation_sections[0].get("default_text", "")
            else:
                items = []
                for s in recommendation_sections:
                    items.append(
                        {
                            "id": s.get("id"),
                            "label": s.get("label"),
                            "text": s.get("default_text", ""),
                            "export_targets": s.get("export_targets", []),
                            "order": s.get("order"),
                            "rich": s.get("rich", True),
                        }
                    )
                form.recommendations_block.data = json.dumps(items, indent=2)

        # Let the parent do any default prefill work as well
        return super().on_form_prefill(form, id)

class NormalMeasurementAdmin(ModelView):
    # List view
    column_list = (
        'name',
        'body_part',
        'modality',
        'module',
        'min_value',
        'max_value',
        'unit',
        'age_group',
        'sex',
        'is_active',
        'created_at',
    )
    column_searchable_list = ('name', 'tags', 'context', 'reference_text')
    column_filters = ('body_part', 'modality', 'module', 'age_group', 'sex', 'is_active')

    form_columns = (
        'name',
        'body_part',
        'modality',
        'module',
        'min_value',
        'max_value',
        'unit',
        'age_group',
        'sex',
        'context',
        'reference_text',
        'reference_doi',
        'tags',
        'is_active',
    )

    form_args = {
        'name': {
            'label': 'Measurement name',
            'render_kw': {
                'placeholder': 'e.g. Appendix diameter, CBD calibre, Main PA diameter'
            }
        },
        'context': {
            'label': 'How / when to measure',
            'render_kw': {
                'placeholder': (
                    'e.g. Measure outer wall-to-outer wall in axial CT at portal venous phase '
                    'at the level of the tracheal bifurcation. Also note what value is abnormal '
                    'and why it matters clinically.'
                )
            },
            'description': (
                'Plain text or HTML. Describe EXACTLY how you measure and when to apply this.'
            )
        },
        'reference_text': {
            'label': 'Reference / interpretation notes',
            'render_kw': {
                'placeholder': (
                    'Key lines from guideline or article; how to interpret high/low values.'
                )
            },
            'description': 'Plain text or HTML; you can paste quotes, short paragraphs, and links.'
        },
        'reference_doi': {
            'label': 'DOI / URL',
            'render_kw': {
                'placeholder': 'e.g. 10.1148/radiol.2018180736 or https://doi.org/...'
            }
        },
        'tags': {
            'label': 'Search tags',
            'render_kw': {
                'placeholder': (
                    'Comma-separated: e.g. appendicitis, RLQ pain, acute abdomen, paediatric, US.'
                )
            },
            'description': 'Used by workstation search & live suggestions.'
        },
        'age_group': {
            'label': 'Age group',
            'render_kw': {
                'placeholder': 'e.g. adult, paediatric, neonate, 50–70y'
            }
        },
        'sex': {
            'label': 'Sex',
            'render_kw': {
                'placeholder': 'male / female / any'
            }
        },
        'unit': {
            'label': 'Unit',
            'render_kw': {
                'placeholder': 'e.g. mm, cm, m/s'
            }
        }
    }

    form_widget_args = {
        'reference_text': {'rows': 5},
        'context': {'rows': 3},
        'tags': {'rows': 2},
    }


# --------------------------------------------------------------------------
# ClassificationSystem admin view
class ClassificationSystemAdmin(ModelView):
    """
    Admin view for ClassificationSystem.

    Exposes modality, body_part, module, and tags so that
    Case Workspace smart search can use structured metadata.
    """

    # List view: show key structured fields
    column_list = (
        'name',
        'short_code',
        'modality',
        'body_part',
        'module',
        'version',
        'tags',
    )

    column_searchable_list = (
        'name',
        'short_code',
        'description',
        'version',
        'tags',
    )

    column_filters = (
        'modality',
        'body_part',
        'module',
    )

    form_columns = (
        'name',
        'short_code',
        'description',
        'version',
        'modality',
        'body_part',
        'module',
        'tags',
    )


class BulletGroupForm(Form):
    title = StringField('List title (optional)')
    style = SelectField(
        'List type',
        choices=[('bullets', 'Bullet list'), ('checkbox', 'Checkbox list')],
        default='bullets',
    )
    items = TextAreaField(
        'Items (one per line)',
        render_kw={'rows': 4, 'placeholder': 'One item per line'}
    )


class TableForm(Form):
    title = StringField('Table title (optional)')
    data = TextAreaField(
        'Table data (one row per line; columns separated by TAB or |; first row is header)',
        render_kw={
            'rows': 6,
            'placeholder': 'Criterion | Points\nClinical signs of DVT | 3\nHeart rate > 100 bpm | 1.5',
        },
    )

# --------------------------------------------------------------------------
# SmartHelperCard admin view

class SmartHelperCardAdmin(ModelView):
    """Admin view for SmartHelperCard.

    New design:
    - No more clever parsing of one big textarea.
    - Explicit bullet_groups (0–many) and tables (0–many) using FieldList + subforms.
    - All structured data stored in definition_json["bullet_groups"] and definition_json["tables"].
    """
    create_template = 'admin/smart_helper_card_edit.html'
    edit_template = 'admin/smart_helper_card_edit.html'

    # Do not show raw JSON and audit fields directly
    form_excluded_columns = (
        "bullets_json",
        "insert_options_json",
        "definition_json",
        "created_at",
        "updated_at",
    )

    # List view configuration
    column_list = (
        "title",
        "token",
        "section",
        "kind",
        "modality",
        "body_part",
        "module",
        "source",
        "source_detail",
        "is_active",
        "priority",
        "bullets_preview",
        "tables_preview",
        "generated_for_token",
        "expires_at",
        "updated_at",
    )

    column_filters = (
        "section",
        "kind",
        "modality",
        "body_part",
        "module",
        "is_active",
        "source",
        "source_detail",
    )

    column_searchable_list = (
        "title",
        "token",
        "summary",
        "tags",
    )

    # Extra helper fields for editing JSON content via proper subforms
    form_extra_fields = {
        # Bullet / checkbox lists: 1–many groups (at least one empty subform by default)
        "bullet_groups": FieldList(
            FormField(BulletGroupForm),
            min_entries=1,
            label="Bullet / checkbox lists",
        ),
        # Tables: 1–many tables (at least one empty subform by default)
        "tables": FieldList(
            FormField(TableForm),
            min_entries=1,
            label="Tables (paste from Excel / Word)",
        ),
        # Insert options as raw JSON
        "insert_options_json_text": TextAreaField(
            "Insert options (advanced JSON)",
            description=(
                "Optional list of insertable report phrases.\n"
                "Format: JSON array of objects, e.g.:\n"
                "[\n"
                "  {\"label\": \"Insert normal PE conclusion\", \"text\": \"No CT evidence of PE.\"}\n"
                "]"
            ),
            render_kw={"rows": 4},
        ),
        # Full advanced definition JSON override (for power users)
        "definition_json_text": TextAreaField(
            "Advanced definition JSON",
            description=(
                "Optional advanced JSON for this helper card. "
                "If provided and valid, it becomes the base definition into which "
                "bullet_groups and tables are injected."
            ),
            render_kw={"rows": 6},
        ),
        # Read-only preview
        "preview_block": TextAreaField(
            "Preview (read-only)",
            description=(
                "Approximate rendering of this helper card based on bullets/tables. "
                "This is for visual feedback only; edit the fields above to change it."
            ),
            render_kw={
                "readonly": True,
                "rows": 6,
                "style": "font-size:0.85rem; background-color:#f8f9fa;",
            },
        ),
        "bullets_json_preview": TextAreaField(
            "Stored bullets_json (read-only)",
            render_kw={"readonly": True, "rows": 3, "style": "font-family: monospace; font-size: 0.85rem;"},
        ),
        "definition_json_preview": TextAreaField(
            "Stored definition_json (read-only)",
            render_kw={"readonly": True, "rows": 4, "style": "font-family: monospace; font-size: 0.85rem;"},
        ),
    }

    # Core form fields, grouped into logical sections
    form_create_rules = form_edit_rules = [
        # High-level toggles and filters
        rules.FieldSet(
            (
                "is_active",
                "section",
                "kind",
                "token",
                "modality",
                "body_part",
                "module",
                "min_age_years",
                "max_age_years",
                "sex",
                "priority",
                "source_detail",
                "source",
                "generated_for_token",
                "generated_hash",
                "expires_at",
                "tags",
            ),
            "Meta / filters",
        ),

        # Core content header
        rules.FieldSet(
            (
                "title",
                "summary",
            ),
            "Helper title & summary",
        ),

        # Bullet / checkbox lists and tables (tidied layout)
        rules.Header("Lists & tables"),
        rules.FieldSet(("bullet_groups",), "Bullet / checkbox lists"),
        rules.HTML('<div style="clear:both; margin: 10px 0;"></div>'),
        rules.FieldSet(("tables",), "Tables (paste from Excel / Word)"),

        # Advanced JSON options
        rules.Header("Advanced JSON options"),
        "insert_options_json_text",
        "definition_json_text",

        # Read-only preview
        rules.Header("Preview"),
        "preview_block",
        "bullets_json_preview",
        "definition_json_preview",
    ]

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        flash("Admin access required.", "warning")
        return redirect(url_for("app_user.login"))

    form_widget_args = {
        # AI provenance fields should generally be read-only in the admin UI
        "generated_for_token": {"readonly": True},
        "generated_hash": {"readonly": True},
    }

    column_formatters = {
        "bullets_preview": lambda v, c, m, p: SmartHelperCardAdmin._format_bullets(m),
        "tables_preview": lambda v, c, m, p: SmartHelperCardAdmin._format_tables(m),
    }

    form_overrides = {
        "source": SelectField,
        "source_detail": SelectField,
    }

    form_args = {
        "source": {
            "choices": [
                ("playbook", "Playbook (static)"),
                ("admin", "Admin (curated in DB)"),
                ("ai-unverified", "AI generated (unverified)"),
                ("ai-verified", "AI generated (verified/updated)"),
            ]
        },
        "source_detail": {
            "choices": [
                ("", "None"),
                ("ai-new", "AI generated (new)"),
                ("ai-verified", "AI verified/updated"),
                ("ai-db", "AI cached in DB"),
            ]
        },
    }

    form_choices = {
        "source": [
            ("playbook", "Playbook (static)"),
            ("admin", "Admin (curated in DB)"),
            ("ai-unverified", "AI generated (unverified)"),
            ("ai-verified", "AI generated (verified/updated)"),
        ],
        "source_detail": [
            ("", "None"),
            ("ai-verified", "AI verified/updated"),
        ],
    }

    column_labels = {
        "bullets_preview": "Bullets",
        "tables_preview": "Tables",
    }

    @expose("/edit/", methods=("GET", "POST"))
    def edit_view(self, *args, **kwargs):
        """
        Flask-Admin injects cls=self; strip it then delegate to base.
        """
        kwargs.pop("cls", None)
        try:
            return super().edit_view(*args, **kwargs)
        except TypeError:
            kwargs.pop("cls", None)
            return super().edit_view(*args, **kwargs)

    @staticmethod
    def _format_bullets(model):
        try:
            bullets = model.bullets_json or []
            if not isinstance(bullets, list):
                return ""
            return f"{len(bullets)} bullet(s)"
        except Exception:
            return ""

    @staticmethod
    def _format_tables(model):
        try:
            definition = model.definition_json or {}
            tables = definition.get("tables") if isinstance(definition, dict) else []
            if not tables:
                return ""
            return f"{len(tables)} table(s)"
        except Exception:
            return ""

    # ---------- Small JSON helpers ----------

    def _parse_json_text_generic(self, raw_value):
        """Generic parser for JSON textareas.

        - Empty -> None
        - Non-empty -> attempt json.loads, flash warning on failure.
        """
        raw_value = (raw_value or "").strip()
        if not raw_value:
            return None
        try:
            return json.loads(raw_value)
        except Exception as exc:
            flash(f"Could not parse JSON: {exc}", "warning")
            return None

    def _stringify_json_generic(self, value):
        if value is None:
            return ""
        try:
            return json.dumps(value, indent=2, ensure_ascii=False)
        except Exception:
            return str(value)

    def _parse_insert_options_text(self, raw_value):
        """Parse insert options from JSON or a simple line-based format.

        Supported formats:
        - Proper JSON (e.g. [{"label": "...", "text": "..."}, ...])
        - One option per line, either:
          - "Label | Text"
          - "Label: Text"
          - or just "Text" (label == text)
        """
        raw = (raw_value or "").strip()
        if not raw:
            return None

        # First try JSON (strict)
        try:
            return json.loads(raw)
        except Exception:
            pass

        # Fallback: simple line-based syntax
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if not lines:
            return None

        options = []
        for ln in lines:
            label = text = ln
            if "|" in ln:
                parts = [p.strip() for p in ln.split("|", 1)]
                if len(parts) == 2:
                    label, text = parts
            elif ":" in ln:
                parts = [p.strip() for p in ln.split(":", 1)]
                if len(parts) == 2:
                    label, text = parts
            options.append({"label": label, "text": text})

        # Inform the user that we used the fallback parser
        flash(
            "Insert options saved using simple line format (label | text). "
            "For full control, provide valid JSON.",
            "info",
        )
        return options

    # ---------- Save logic ----------

    def _populate_base_fields(self, form, model):
        """Populate only real model fields, skipping helper FieldLists/JSON preview fields."""
        helper_names = {
            "bullet_groups",
            "tables",
            "insert_options_json_text",
            "definition_json_text",
            "preview_block",
        }
        skip_names = helper_names.union({"csrf_token", "submit", "_continue_editing"})

        for name, field in getattr(form, "_fields", {}).items():
            if name in skip_names:
                continue
            try:
                field.populate_obj(model, name)
            except Exception:
                # Ignore fields that cannot be directly populated (e.g. read-only helpers)
                continue

    def create_model(self, form):
        """Custom create_model to avoid populate_obj issues with helper FieldLists."""
        try:
            model = self.model()
            # Populate basic scalar/enum fields
            self._populate_base_fields(form, model)
            # Let on_model_change handle bullets/tables/JSON helpers
            self.on_model_change(form, model, True)
            db.session.add(model)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            flash(f"Failed to create record: {exc}", "error")
            return False
        else:
            return True

    def update_model(self, form, model):
        """Custom update_model to avoid populate_obj issues with helper FieldLists."""
        try:
            # Populate basic scalar/enum fields
            self._populate_base_fields(form, model)
            # Let on_model_change handle bullets/tables/JSON helpers
            self.on_model_change(form, model, False)
            db.session.add(model)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            flash(f"Failed to update record: {exc}", "error")
            return False
        else:
            return True

    def on_model_change(self, form, model, is_created):
        """Sync subforms into JSON columns before saving."""
        # ---- Bullet groups -> bullets_json + definition_json["bullet_groups"] ----
        bullet_groups = []
        if hasattr(form, "bullet_groups"):
            for entry in form.bullet_groups:
                title = (entry.title.data or "").strip() or None
                style = (entry.style.data or "bullets").strip()
                if style not in ("bullets", "checkbox"):
                    style = "bullets"
                items_raw = entry.items.data or ""
                items = [line.strip() for line in items_raw.splitlines() if line.strip()]
                if not items:
                    continue
                bullet_groups.append(
                    {
                        "title": title,
                        "style": style,
                        "items": items,
                    }
                )

        model.bullets_json = bullet_groups or None

        # ---- Insert options from JSON textarea (with friendly fallback) ----
        if hasattr(form, "insert_options_json_text"):
            model.insert_options_json = self._parse_insert_options_text(
                form.insert_options_json_text.data
            )

        # ---- Base definition_json ----
        base_def = model.definition_json or {}

        # Advanced override, if provided and valid
        advanced = None
        if hasattr(form, "definition_json_text") and form.definition_json_text.data:
            advanced = self._parse_json_text_generic(form.definition_json_text.data)

        if isinstance(advanced, dict):
            base_def = advanced
        elif isinstance(advanced, list):
            base_def = {"sections": advanced}
        elif not isinstance(base_def, dict):
            base_def = {}

        # Ensure meta exists
        base_def.setdefault("meta", {})

        # ---- Tables from FieldList(TableForm) -> definition_json["tables"] ----
        tables_struct = []
        splitter = re.compile(r"\t|\|")

        if hasattr(form, "tables"):
            for entry in form.tables:
                # Each entry is a FormField(TableForm); use the inner form for fields
                inner = getattr(entry, "form", entry)

                raw_data = (getattr(getattr(inner, "data", None), "data", "") or "").strip()
                if not raw_data:
                    continue

                title = (getattr(inner, "title").data or "").strip() or None

                lines = [ln.strip() for ln in raw_data.splitlines() if ln.strip()]
                if not lines:
                    continue

                # First line assumed header; if it produces no real cells, we'll auto-generate
                header_cells = [c.strip() for c in splitter.split(lines[0])] if lines else []

                # If header row is effectively empty, treat all lines as data and auto-header
                if not any(header_cells):
                    data_rows_raw = []
                    max_cols = 0
                    for ln in lines:
                        cells = [c.strip() for c in splitter.split(ln)]
                        if not any(cells):
                            continue
                        data_rows_raw.append(cells)
                        max_cols = max(max_cols, len(cells))

                    if max_cols == 0:
                        continue

                    headers = [f"Col {i+1}" for i in range(max_cols)]
                    rows = []
                    for cells in data_rows_raw:
                        if len(cells) < max_cols:
                            cells = cells + [""] * (max_cols - len(cells))
                        else:
                            cells = cells[:max_cols]
                        rows.append(cells)
                else:
                    headers = header_cells
                    max_cols = len(headers)
                    rows = []
                    for ln in lines[1:]:
                        cells = [c.strip() for c in splitter.split(ln)]
                        if not any(cells):
                            continue
                        if len(cells) < max_cols:
                            cells = cells + [""] * (max_cols - len(cells))
                        else:
                            cells = cells[:max_cols]
                        rows.append(cells)

                if not rows:
                    continue

                tables_struct.append(
                    {
                        "title": title,
                        "headers": headers,
                        "rows": rows,
                    }
                )

        if tables_struct:
            base_def["tables"] = tables_struct
        else:
            base_def.pop("tables", None)

        if bullet_groups:
            base_def["bullet_groups"] = bullet_groups
        else:
            base_def.pop("bullet_groups", None)

        # Assign back
        model.definition_json = base_def or None

        return super().on_model_change(form, model, is_created)

    # ---------- Prefill logic ----------

    def on_form_prefill(self, form, id):
        """Populate FieldLists and JSON textareas from the model before editing."""
        model = self.get_one(id)
        if not model:
            return super().on_form_prefill(form, id)

        definition = model.definition_json or {}

        # ---- Bullet groups ----
        bullet_groups = definition.get("bullet_groups")
        if bullet_groups is None:
            bullet_groups = model.bullets_json

        if hasattr(form, "bullet_groups") and isinstance(bullet_groups, list):
            # Clear any default empty entries
            while len(form.bullet_groups.entries):
                form.bullet_groups.pop_entry()

            for group in bullet_groups:
                if not isinstance(group, dict):
                    continue
                sub = form.bullet_groups.append_entry()
                sub.title.data = group.get("title") or ""
                style = group.get("style") or "bullets"
                if style not in ("bullets", "checkbox"):
                    style = "bullets"
                sub.style.data = style
                items = group.get("items") or []
                if isinstance(items, list):
                    sub.items.data = "\n".join(str(i) for i in items)
                else:
                    sub.items.data = str(items)

        # Ensure at least one empty bullet group entry if none exist
        if hasattr(form, "bullet_groups") and not form.bullet_groups.entries:
            form.bullet_groups.append_entry()

        # ---- Tables ----
        tables_struct = definition.get("tables") or []

        if hasattr(form, "tables") and isinstance(tables_struct, list):
            while len(form.tables.entries):
                form.tables.pop_entry()

            for tbl in tables_struct:
                if not isinstance(tbl, dict):
                    continue
                sub = form.tables.append_entry()
                inner = getattr(sub, "form", sub)
                inner.title.data = (tbl.get("title") or "")

                headers = tbl.get("headers") or []
                rows = tbl.get("rows") or []
                lines = []
                if headers:
                    lines.append(" | ".join(str(h) for h in headers))
                for row in rows:
                    lines.append(" | ".join(str(c) for c in (row or [])))
                inner.data.data = "\n".join(lines)

        # Ensure at least one empty table entry if none exist
        if hasattr(form, "tables") and not form.tables.entries:
            form.tables.append_entry()

        # ---- Insert options JSON ----
        if hasattr(form, "insert_options_json_text"):
            form.insert_options_json_text.data = self._stringify_json_generic(
                model.insert_options_json
            )

        # ---- Full definition JSON ----
        if hasattr(form, "definition_json_text"):
            form.definition_json_text.data = self._stringify_json_generic(
                model.definition_json
            )

        # ---- Read-only previews of stored JSON ----
        if hasattr(form, "bullets_json_preview"):
            form.bullets_json_preview.data = self._stringify_json_generic(
                model.bullets_json
            )
        if hasattr(form, "definition_json_preview"):
            form.definition_json_preview.data = self._stringify_json_generic(
                model.definition_json
            )

        # ---- Preview ----
        if hasattr(form, "preview_block") and model:
            try:
                vm = serialize_smart_helper_card(model) or {}

                def _vm_get(obj, key, default=None):
                    if isinstance(obj, dict):
                        return obj.get(key, default)
                    return getattr(obj, key, default)

                lines = []
                title = _vm_get(vm, "title") or getattr(model, "title", None) or "(No title)"
                kind_label = _vm_get(vm, "kind_label") or _vm_get(vm, "kind") or (
                    str(model.kind) if hasattr(model, "kind") else "Info"
                )
                section_label = _vm_get(vm, "section_label") or _vm_get(vm, "section") or (
                    str(model.section) if hasattr(model, "section") else "Any section"
                )
                meta = _vm_get(vm, "meta_text") or ""

                lines.append(f"Title: {title}")
                lines.append(f"Kind: {kind_label} | Section: {section_label}")
                if meta:
                    lines.append(f"Context: {meta}")

                display_mode = _vm_get(vm, "display_mode") or "list"
                rows = _vm_get(vm, "rows") or []
                bullets = _vm_get(vm, "bullets") or []

                lines.append("")
                if display_mode == "table" and rows:
                    lines.append("Table mode (label: value):")
                    for r in rows:
                        lbl = _vm_get(r, "label", "")
                        val = _vm_get(r, "value_html", "")
                        lines.append(f"- {lbl}: {val}")
                elif bullets:
                    lines.append("List mode (bullets):")
                    for b in bullets:
                        lines.append(f"- {b}")
                else:
                    summary = (
                        _vm_get(vm, "summary_html")
                        or _vm_get(vm, "summary")
                        or ""
                    ).strip()
                    if summary:
                        lines.append("Summary:")
                        lines.append(summary)

                form.preview_block.data = "\n".join(lines) if lines else "No preview available yet."
            except Exception as exc:
                flash(f"Could not build SmartHelper preview: {exc}", "warning")
                form.preview_block.data = ""

        return super().on_form_prefill(form, id)
