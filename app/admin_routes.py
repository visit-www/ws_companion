# * Imports
from flask import Blueprint, request, render_template, redirect, url_for, flash, session, jsonify,send_file
from sqlalchemy import inspect, Table,MetaData
from flask_login import login_required, current_user
from .models import User, Content
from io import BytesIO
from flask import send_file
import os
import tempfile
import shutil
import json
from datetime import datetime, timezone
from .models import User, Content, AdminReportTemplate, ClassificationSystem, ImagingProtocol, NormalMeasurement, UserAnalyticsEvent,db,Base
import difflib


# * Blueprint setup
app_admin_bp = Blueprint(
    'app_admin', __name__,
    static_folder='static',
    static_url_path='/static'
)

#todo: Global Error Handling
#@app_admin_bp.errorhandler(Exception)
#def handle_exception(e):
#    app_admin_bp.logger.error(f"Unhandled Exception in Admin Blueprint: {e}", exc_info=True)
#    return jsonify({'error': 'An internal error occurred'}), 500



# * Admin Dashboard Route
@app_admin_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('user.login'))

    # Handle admin dashboard action buttons (POST)
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_contents':
            return redirect(url_for('app_admin.add_contents'))
        elif action == 'user_management':
            return redirect(url_for('app_admin.user_management'))
        elif action == 'reset_database':
            return redirect(url_for('app_admin.reset_database'))
        elif action == 'reset_users':
            return redirect(url_for('app_admin.reset_users'))

    # Basic dashboard context
    users = db.session.query(User).all()
    contents = db.session.query(Content).all()

    # Optional breadcrumb data (can be used or ignored by the template)
    breadcrumbs = [
        {'label': 'Home', 'url': url_for('main_routes.index')},
        {'label': 'Admin', 'url': url_for('app_admin.admin_dashboard')},
        {'label': 'Dashboard', 'url': None},
    ]

    return render_template(
        'admin_dashboard.html',
        users=users,
        contents=contents,
        breadcrumbs=breadcrumbs,
    )

# *-----------------------------------------------------------------------------------
# dd a simple page where you can see counts of:
    # Templates
    # Classification systems
    # Protocols
    # Normal measurements
    # Recent analytics
# *-----------------------------------------------------------------------------------
@app_admin_bp.route("/tools-overview", methods=["GET"])
@login_required
def tools_overview():
    if not current_user.is_admin:
        flash("Admin access required.", "danger")
        return redirect(url_for("main_routes.index"))

    templates_count = db.session.query(AdminReportTemplate).count()
    classification_count = db.session.query(ClassificationSystem).count()
    protocol_count = db.session.query(ImagingProtocol).count()
    normal_measurements_count = db.session.query(NormalMeasurement).count()
    events_count = db.session.query(UserAnalyticsEvent).count()

    return render_template(
        "admin/tools_overview.html",
        templates_count=templates_count,
        classification_count=classification_count,
        protocol_count=protocol_count,
        normal_measurements_count=normal_measurements_count,
        events_count=events_count,
    )
#*----------------------------------------------------------------
# View all the models/tables in one place :
@app_admin_bp.route('/models')
@login_required
def view_models():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main_routes.index'))
    
    # Read search query from URL (?q=imaging, ?q=protcol, etc.)
    search_query = request.args.get('q', '').strip()
    
    # Use the Base metadata to get all model (table) names
    model_names = sorted(Base.metadata.tables.keys())
    
    # Build initial table data
    tables_data = [
        {
            'table_name': table_name,
            'endpoint': table_name,
        }
        for table_name in model_names
    ]
    
    # Apply flexible search if a query is provided
    if search_query:
        tokens = [t.lower() for t in search_query.split() if t.strip()]
        filtered_tables = []
        
        for t in tables_data:
            name = t['table_name']
            name_lower = name.lower()
            
            # Split table name into parts for better fuzzy matching
            parts = name_lower.replace('_', ' ').split()
            
            def token_matches(token: str) -> bool:
                # Direct substring match
                if token in name_lower:
                    return True
                # Fuzzy match against each part of the table name
                for part in parts:
                    ratio = difflib.SequenceMatcher(a=token, b=part).ratio()
                    if ratio >= 0.7:  # allow minor spelling mistakes
                        return True
                return False
            
            # If any token matches (substring or fuzzy), keep this table
            if any(token_matches(tok) for tok in tokens):
                filtered_tables.append(t)
        
        tables_data = filtered_tables
    
    # Breadcrumbs for the models page
    breadcrumbs = [
        {'label': 'Home', 'url': url_for('main_routes.index')},
        {'label': 'Admin', 'url': url_for('app_admin.admin_dashboard')},
        {'label': 'Models', 'url': None},
    ]
    
    # Pass the list of tables data and search/breadcrumb context to the template
    return render_template(
        'tables.html',
        tables_data=tables_data,
        search_query=search_query,
        breadcrumbs=breadcrumbs,
    )
#*----------------------------------------------------------------
@app_admin_bp.route('/manage-model', methods=['GET', 'POST'])
@login_required
def manage_model():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main_routes.index'))

    # Get the action and button ID from the form
    action = request.form.get('action')
    button_id = request.form.get('button_id')

    # Use the Base metadata to get all model (table) names
    model_names = Base.metadata.tables.keys()
    if action == "add_data" and button_id in model_names:
        # If action is 'add_data' and button ID matches a model name, redirect to the correct URL
        # Construct the URL to add new entries to the model via Flask-Admin
        target_url = f"/flask_admin/{button_id}/new/"
        return redirect(target_url)
    # ! Debugging 
    # If no specific action matches, render the test page with tables data and message in console
    return render_template(url_for('main_routes.debug'))
# *----------------------------------------------------------------
# create smart report templates:
# *----------------------------------------------------------------

# Import the two form classes
from .forms import AddReportTemplateMobile, AddReportTemplateDesktop

@app_admin_bp.route('/create_report_templates', methods=['GET', 'POST'])
@login_required
def create_report_template():
    # Initialize forms with prefixes
    mobile_form = AddReportTemplateMobile(prefix='mobile')
    desktop_form = AddReportTemplateDesktop(prefix='desktop')
    
    if request.method == 'POST':
        # Determine which form was submitted
        if 'submit_mobile' in request.form:
            submitted_form = mobile_form
            form_type = 'mobile'
        elif 'submit_desktop' in request.form:
            submitted_form = desktop_form
            form_type = 'desktop'
        else:
            # Unknown submission, re-render with initialized forms
            flash("Unknown form submission.", "error")
            return render_template('create_smart_report_template.html', mobile_form=mobile_form, desktop_form=desktop_form)
        
        # Validate the submitted form
        if submitted_form.validate_on_submit():
            report_type = request.form.getlist('report_type')
            # Process the form data here
            flash("Form successfully submitted!", "success")
        else:
            flash("There were validation errors. Please correct them and resubmit.", "error")
    
    # Re-instantiate forms with prefixes to ensure consistency for the next render
    mobile_form = AddReportTemplateMobile(prefix='mobile')
    desktop_form = AddReportTemplateDesktop(prefix='desktop')
    
    # Render the template with re-initialized forms
    return render_template('create_smart_report_template.html', mobile_form=mobile_form, desktop_form=desktop_form)

# *-------------------------Route to save report, download report and preivew reports---------------------------------------
from flask import request, render_template, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from datetime import datetime, timezone
from io import BytesIO
import os, zipfile, json

from app import db
from app.models import UserReportTemplate
from app.forms import AddReportTemplateMobile, AddReportTemplateDesktop
from app.util import create_report_template_pdf, create_report_template_word, cleanup_old_previews

@app_admin_bp.route('/save_report_template', methods=['POST'])
@login_required
def save_report_template():
    mobile_form = AddReportTemplateMobile(prefix='mobile')
    desktop_form = AddReportTemplateDesktop(prefix='desktop')

    # Determine submitted form
    form_type = 'mobile' if 'mobile-template_name' in request.form else 'desktop'
    submitted_form = mobile_form if form_type == 'mobile' else desktop_form

    # Check user action
    is_preview = 'preview_report' in request.form
    is_save = 'save_report' in request.form
    is_export = 'desktop-submit_desktop' in request.form or 'mobile-submit_mobile' in request.form
    
    if not submitted_form.validate_on_submit():
        return render_template('create_smart_report_template.html',
                        mobile_form=mobile_form,
                        desktop_form=desktop_form)
    # Gather form data
    data = {
        'template_name': submitted_form.template_name.data or "Untitled",
        'name': submitted_form.name.data or "Unknown",
        'gender': submitted_form.gender.data or "Unspecified",
        'patient_id': submitted_form.patient_id.data or "N/A",
        'age': submitted_form.age.data or "N/A",
        'dob': submitted_form.dob.data or "N/A",
        'location': submitted_form.location.data or "N/A",
        'clinical_info': submitted_form.clinical_info.data or "None",
        'technical_info': submitted_form.technical_info.data or "None",
        'comparison': submitted_form.comparison.data or "None",
        'observations': [
            {
                'section': obs.section.data or "Untitled Section",
                'details': obs.details.data or "No details provided"
            } for obs in submitted_form.observations
        ],
        'conclusions': submitted_form.conclusions.data or "None",
        'recommendations': submitted_form.recommendations.data or "None"
    }

    # ✅ Save Report and Show Preview
    if is_save:
        template = UserReportTemplate(
            template_name=data['template_name'],
            user_id=current_user.id,
            template_text=json.dumps(data),
            is_public=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.session.add(template)
        db.session.commit()

        # Generate preview
        preview_folder = os.path.join('user_data', 'preview_reports')
        os.makedirs(preview_folder, exist_ok=True)

        filename = f"preview_saved_{template.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}.pdf"
        filepath = os.path.join(preview_folder, filename)

        pdf_stream = create_report_template_pdf(data)
        with open(filepath, 'wb') as f:
            f.write(pdf_stream.read())

        cleanup_old_previews(preview_folder, age_minutes=30)
        file_url = request.args.get("file_url")
        # 🔗 Construct relative file URL (for iframe embedding)
        file_url = url_for('main_routes.static_preview', filename=filename, _external=True)

        # 🔁 Optional: switch viewer via query string (e.g. &viewer=pspdfkit)
        viewer = request.args.get('viewer', 'mozilla')
        template_name = 'mozilla_pdfjs_viewer.html' if viewer == 'mozilla' else 'pspdfkit_viewer.html'
        print(f'template being used is :{template_name}')
        return render_template(
            template_name,
            file_url=file_url,
            file_name=filename,
            back_url=request.referrer or url_for('main_routes.index')
        )

    # ✅ Preview Report as PDF
    if is_preview:
        preview_folder = os.path.join('user_data', 'preview_reports')
        os.makedirs(preview_folder, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        filename = f"preview_{timestamp}.pdf"
        filepath = os.path.join(preview_folder, filename)

        # Save generated PDF
        with open(filepath, 'wb') as f:
            f.write(create_report_template_pdf(data).read())

        # Cleanup old preview files
        cleanup_old_previews(preview_folder, age_minutes=15)

        # 🔗 Construct relative file URL (for iframe embedding)
        file_url = url_for('main_routes.static_preview', filename=filename, _external=True)

        # 🔁 Optional: switch viewer via query string (e.g. &viewer=pspdfkit)
        viewer = request.args.get('viewer', 'mozilla')
        template_name = 'mozilla_pdfjs_viewer.html' if viewer == 'mozilla' else 'pspdfkit_viewer.html'
        print(f'template being used is :{template_name}')
        return render_template(
            template_name,
            file_url=file_url,
            file_name=filename,
            back_url=request.referrer or url_for('main_routes.index')
        )
    # ✅ Export PDF/Word
    if is_export:
        print ('export requested-----------------')
        report_type = request.form.getlist('report_type')
        if not report_type:
            flash("Please select at least one report type (PDF or Word).", "error")
            return redirect(request.referrer or url_for('app_admin.smart_report_form'))
        files, filenames = [], []
        if not report_type:
            flash("Please select at least one report type (PDF or Word).", "error")
            return redirect(request.referrer or url_for('app_admin.smart_report_form'))
        

        if 'pdf' in report_type:
            pdf_file = create_report_template_pdf(data)
            files.append(pdf_file)
            filenames.append('report_template.pdf')

        if 'word' in report_type:
            word_file = create_report_template_word(data, 'word')
            files.append(word_file)
            filenames.append('report_template.docx')

        if not files:
            print(f'No file generated. Please select at least one format.')
            flash("No file generated. Please select at least one format.", "error")
            return redirect(request.url)

        if len(files) == 1:
            file_stream, filename = files[0], filenames[0]
            mime = 'application/pdf' if filename.endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            file_stream.seek(0)
            return send_file(file_stream, as_attachment=True, download_name=filename, mimetype=mime)

        # Create zip for multiple files
        zip_stream = BytesIO()
        with zipfile.ZipFile(zip_stream, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f, fname in zip(files, filenames):
                f.seek(0)
                zf.writestr(fname, f.read())
        zip_stream.seek(0)
        return send_file(zip_stream, as_attachment=True, download_name='report_templates.zip', mimetype='application/zip')

    # If none of the conditions met
    flash("Invalid request. Please try again.", "error")
    return render_template('create_smart_report_template.html', mobile_form=mobile_form, desktop_form=desktop_form)
#----------------------------------------------------------------

# todo: Placeholder route for adding contents
@app_admin_bp.route('/reset_database', methods=['GET', 'POST'])
@login_required
def reset_db():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('app_user.login'))
    
    action = request.form.get('action', '')
    button_id = request.form.get('button_id', '')

    if action == "reset_users" and button_id == "users":
        # Retrieve all users except admins
        users_to_delete = db.session.query(User).filter(User.is_admin == False).all()

        # Delete non-admin users
        for user in users_to_delete:
            db.session.delete(user)

        # Commit the session to trigger cascading
        try:
            db.session.commit()
            flash("All users except admins deleted.", 'warning')
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while deleting users: {e}", 'danger')

        return redirect('/flask_admin/users')

    elif action == 'reset_db' and button_id == 'db':
        flash("The resetting of the database is not enabled. Please contact the owner of the App if you want to perform this action.", 'warning')
        return redirect(url_for('app_admin.view_models'))
#!----------------------------------------------------------------

# Developer resources: Git workflow route
@app_admin_bp.route('/developer-resources/git-workflow', methods=['GET'])
@login_required
def developer_git_workflow():
    if not current_user.is_admin:
        flash('Access restricted to administrators only.', 'warning')
        return redirect(url_for('main_routes.index'))
    return render_template('developer_resources/git_workflow.html')