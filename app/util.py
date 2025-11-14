# * Imports
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app

def generate_password_reset_token(data, expiration=600):
    """Generate a secure token for given data."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(data, salt=current_app.config['SECURITY_PASSWORD_SALT'])

def verify_password_reset_token(token, expiration=600):
    """Verify a password reset token and return the associated data if valid."""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = serializer.loads(token, salt=current_app.config['SECURITY_PASSWORD_SALT'], max_age=expiration)
        return data
    except (BadSignature, SignatureExpired):
        return None

#Functions to generate otps using pyotp for mfa:

import pyotp
def generate_otp_secret():
    #Generates a new TOTP secret key
    return pyotp.random_base32()

def generate_otp_token(secret, interval=200):
    #Generates a TOTP token based on the given secret and interval
    totp = pyotp.TOTP(secret, interval=interval)
    return totp.now()

    
# Default app initialization
import json
from datetime import datetime, timezone
from .models import db,Content, User, UserData, UserContentState, AdminReportTemplate
from config import basedir
import os
from config import ADMIN_EMAIL, ADMIN_PASSWORD,ANONYMOUS_EMAIL,ANONYMOUS_PASSWORD,ANONYMOUS_USER_ID

def add_default_admin(admin_data):
    """Add admin user if not already present."""
    admin_user = db.session.query(User).filter_by(email=ADMIN_EMAIL).first()
    try:
        if not admin_user:
            new_admin = User(
                username=admin_data['username'],
                email=ADMIN_EMAIL,
                is_paid=admin_data['is_paid'],
                is_admin=admin_data['is_admin']
            )
            new_admin.set_password(ADMIN_PASSWORD)
            db.session.add(new_admin)
            db.session.commit()
    
            print(f"Admin user created: {new_admin.username}, {new_admin.email}")
    
            # Initialize UserData for the admin
            user_data = UserData(
                user_id=new_admin.id,
                interaction_type='registered',
                time_spent=0,
                last_interaction=datetime.now(timezone.utc),
                last_login=datetime.now(timezone.utc)
            )
            db.session.add(user_data)
    
            # Initialize UserContentState for the admin
            user_content_state = UserContentState(
                user_id=new_admin.id,
                modified_filepath=None,
                annotations=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.session.add(user_content_state)
            # Initialize AdminReportTemplate with
            admin_report_template = AdminReportTemplate(
                template_name=None,
                    body_part= None,
                    modality=None,
                    file=None,
                    filepath=None,
                    tags=None,
                    category=None,
                    module=None,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                    )
            db.session.add(admin_report_template)
            db.session.commit()
            print(f"Admin data initialized.")
        else:
            print(f"Admin already exists: {admin_user.username}")
            print(f"Admin user created: {new_admin.username}, {new_admin.email}")
            print(f"Admin data initialized.")
    except Exception as e:
        print(f"Error adding default admin: {e}")
        db.session.rollback()
        pass
# Crreate Anonymous user to relate to orphaned data after users or content is delated (referecnes, userfeedback)
from config import ANONYMOUS_USER_ID
def add_anonymous_user():
    anonymous_user = db.session.query(User).filter_by(username='anonymous').first()
    try:
        if not anonymous_user:
            # Create anonymous user
            anonymous_user = User(
                id=ANONYMOUS_USER_ID,
                username='anonymous',
                email=ANONYMOUS_EMAIL,
                is_paid=False,
                is_admin=False,
                status='active',
            )
            anonymous_user.set_password(ANONYMOUS_PASSWORD)
            db.session.add(anonymous_user)
            db.session.commit()
            print(f"Anonymous user created: {anonymous_user}, {anonymous_user.email}")
        else:
            print(f"Anonymous user already exists: {anonymous_user.username}")
    except Exception as e:
        print(f"Error adding anonymous user: {e}")
        db.session.rollback()
        pass

def add_default_contents(contents_data):
    """Add default contents if not already present."""
    for content_data in contents_data:
        existing_content = db.session.query(Content).filter_by(title=content_data['title']).first()
        if not existing_content:
            new_content = Content(
                title=content_data['title'],
                category=content_data['category'],
                module=content_data['module'],
                status=content_data['status'],
                external_url=content_data.get('external_url'),
                embed_code=content_data['embed_code'],
                description=content_data['description'],
                created_by=content_data['created_by'],
                language=content_data['language'],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.session.add(new_content)
            print(f"Content added: {new_content.title}")
        else:
            print(f"Content already exists: {existing_content.title}")
    

    db.session.commit()
    print("Default contents loaded successfully.")

def load_default_data():
    """Load default admin and content data from JSON."""
    json_filepath= os.path.join(basedir,'app','default_data.json')
    try:
        with open(json_filepath) as f:
            default_data = json.load(f)
            print("json file loaded")
            return default_data
    except FileNotFoundError:
        print("default_data.json not found")
        return None
    
from flask import url_for
from markupsafe import Markup


def inline_references(content, references):
    """Replace specific terms in content with inline links to references."""
    if not references:
        return content  # Return content as-is if no references are provided

    # Loop through references and replace occurrences of each term with a link
    for ref in references:
        term = ref.title  # Assuming the reference title is the term to match
        link = url_for("content_routes.view_reference", category=ref.category, display_name="References", reference_id=ref.id)
        replacement = f'<a href="{link}" class="reference-link" target="_blank">{term}</a>'
        content = content.replace(term, replacement)  # Replace term with link in content

    return Markup(content)  # Return content as HTML-safe string

def get_anonymous_user_id():
    """Returns the ID of the anonymous user, creating one if necessary."""
    user = db.session.query(User).filter_by(username="anonymous").first()
    if user:
        return user.id
    else:
        add_anonymous_user()
        user = db.session.query(User).filter_by(username="anonymous").first()
        return user.id if user else None
#function related to report generation and report managment :
# ------------------------------------------------------
# Function to clear report preview files
import os, time
def cleanup_old_previews(folder, age_minutes=15):
    now = time.time()
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        if os.path.isfile(path) and filename.endswith('.pdf'):
            if now - os.path.getmtime(path) > age_minutes * 60:
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Error deleting {path}: {e}")
                    
#Functions to create pdf and word report files :
from io import BytesIO
import tempfile
import shutil
from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT, WD_ALIGN_PARAGRAPH
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
def create_report_template_word(data,report_type,return_path_only=False):
    # Initialize document
    doc = Document()
    
    # Hero container (unchanged)
    title_paragraph = doc.add_paragraph()
    title_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    logo_run = title_paragraph.add_run()
    logo = logo_run.add_picture('app/static/assets/images/logo-white-bg.png', height=Inches(0.5))
    title_run = title_paragraph.add_run(" WSC - A Workstation Companion App")
    title_run.bold = True
    title_run.font.size = Pt(20)
    title_run.font.color.rgb = RGBColor(52, 58, 64)
    title_paragraph.space_after = Pt(6)
    
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_run = subtitle.add_run("Simplify your radiology workflow with our intuitive and comprehensive tools.")
    subtitle_run.font.size = Pt(14)
    subtitle_run.font.color.rgb = RGBColor(108, 117, 125)
    subtitle.space_after = Pt(2)
    
    italic_text = doc.add_paragraph()
    italic_text.alignment = WD_ALIGN_PARAGRAPH.CENTER
    italic_run = italic_text.add_run("Because every hero needs a trusty companion.")
    italic_run.italic = True
    italic_run.font.size = Pt(14)
    italic_run.font.color.rgb = RGBColor(40, 167, 69)
    italic_text.space_after = Pt(2)
    
    # Document Title (unchanged)
    title = doc.add_heading('Report Template', level=0)
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    title_run = title.runs[0]
    title_run.font.size = Pt(20)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(0, 100, 0)
    template_name=data.get('template_name')
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle_run = subtitle.add_run(f"{template_name}")
    subtitle_run.font.size = Pt(14)
    subtitle_run.font.color.rgb = RGBColor(108, 117, 125)
    subtitle.space_after = Pt(1)
    # Patient Information Table
    patient_info = {
        'Name': data.get('name', 'No name provided'),
        'Gender': data.get('gender', 'Not specified'),
        'ID': data.get('patient_id', 'No ID provided'),
        'Age': data.get('age', 'Not specified'),
        'DOB': data.get('dob', 'Not specified'),
        'Location': data.get('location', 'No location provided')
    }
    
    table = doc.add_table(rows=3, cols=2)
    table.style = 'Table Grid'
    for idx, (field, value) in enumerate(patient_info.items()):
        row, col = divmod(idx, 2)
        cell = table.cell(row, col)
        cell.text = f"{field}: {value}"
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
            paragraph.runs[0].font.size = Pt(12)
    
    # Clinical information section
    doc.add_heading('Clinical Context:', level=1)
    clinical_info_text = data.get('clinical_info', 'No clinical information provided')
    clinical_info_paragraph = doc.add_paragraph(clinical_info_text if clinical_info_text else 'No clinical information provided')
    clinical_info_paragraph.runs[0].font.size = Pt(12)
    clinical_info_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    clinical_info_paragraph.space_after = Pt(1)
    # technical information section
    doc.add_heading('Protocol/Technique:', level=1)
    technical_info_text = data.get('technical_info', 'No technique related infomration provided')
    technical_info_paragraph = doc.add_paragraph(technical_info_text if technical_info_text else 'No technique related infomration provided')
    technical_info_paragraph.runs[0].font.size = Pt(12)
    technical_info_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    technical_info_paragraph.space_after=Pt(1)
    #Comparison section
    doc.add_heading('Comparisons:', level=1)
    comparison_text = data.get('comparison', 'No relevant priors available for comparison')
    comparison_paragraph = doc.add_paragraph(comparison_text if comparison_text else 'No relevant priors available for comparison')
    comparison_paragraph.runs[0].font.size = Pt(12)
    comparison_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    comparison_paragraph
    # Observations Section
    doc.add_heading('Observations:', level=1)

    # Ensure observations is always a list, with a default empty list if it's None
    observations = data.get('observations', [])

    for obs in observations:
        # Skip any None observation
        if obs is None:
            continue
    
        # Initialize defaults for each observation
        section_name = "Section"  # Default value for section
        detail = "No details provided"  # Default value for details
    
        # Process each key-value pair within the observation
        for key, value in obs.items():
            if key == 'section':
                section_name = value if value else 'Section'  # Replace empty or None with default
            elif key == 'details':
                detail = value if value else 'No details provided'  # Replace empty or None with default

        # Create a new paragraph for each observation with section and details
        obs_paragraph = doc.add_paragraph()

        # Section name in bold
        section_heading = obs_paragraph.add_run(f"{section_name}: ")
        section_heading.bold = True
        section_heading.font.size = Pt(13)
        section_heading.font.color.rgb = RGBColor(0, 102, 204)  # Light Blue
    
        # Details in regular font
        details_run = obs_paragraph.add_run(detail)
        details_run.font.size = Pt(12)
        obs_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT


    # Conclusions Section
    doc.add_heading('Conclusions:', level=1)
    conclusions_text = data.get('conclusions', 'No conclusions provided')
    conclusions_paragraph = doc.add_paragraph(conclusions_text if conclusions_text else 'No conclusions provided')
    conclusions_paragraph.runs[0].font.size = Pt(12)
    conclusions_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    conclusions_paragraph
    # Recommendations Section
    doc.add_heading('Recommendations:', level=1)
    recommendations_text = data.get('recommendations', 'No recommendations provided')
    recommendations_paragraph = doc.add_paragraph(recommendations_text if recommendations_text else 'No recommendations provided')
    recommendations_paragraph.runs[0].font.size = Pt(12)
    recommendations_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    
    # Signature and Footer (unchanged)
    signature = doc.add_paragraph()
    signature_run = signature.add_run("\nReported and electronically signed by:\nRegistration Number:\n")
    signature_run.font.size = Pt(12)
    signature_run.bold = True
    date_run = signature.add_run(f"Dated: {datetime.now().strftime('%Y-%m-%d')}")
    date_run.font.size = Pt(12)
    date_run.italic = True

    section = doc.sections[0]
    footer = section.footer
    footer_paragraph = footer.paragraphs[0]
    footer_paragraph.text = 'SmartReportTemplates\nBrought to you by WSCompanion: because every Hero needs a companion'
    footer_paragraph.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    footer_paragraph.runs[0].font.size = Pt(10)
    footer_paragraph.runs[0].font.color.rgb = RGBColor(107, 142, 35)
    
    # Use a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        word_file_path = os.path.join(temp_dir, "report_template.docx")
        doc.save(word_file_path)
        
        if return_path_only:
            # Since the temporary directory will be deleted after the 'with' block,
            # we need to copy the file if we need the path
            temp_word_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
            temp_word_file.close()
            shutil.copy(word_file_path, temp_word_file.name)
            return temp_word_file.name
        else:
            # Read the file into a BytesIO buffer
            with open(word_file_path, "rb") as word_file:
                file_stream = BytesIO(word_file.read())
            return file_stream


# Function to create pdf document form form data :from fpdf import FPDF
from reportlab.lib.pagesizes import LETTER, A4
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def create_report_template_pdf(data, return_path_only=False):
    # Create a BytesIO buffer to hold the PDF data
    buffer = BytesIO()
    
    # Create a SimpleDocTemplate object
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Build the PDF elements
    elements = []
    
    # Add logo and title
    # Assuming the logo is in 'app/static/assets/images/logo-white-bg.png'
    logo_path = 'app/static/assets/images/logo-white-bg.png'
    try:
        logo = Image(logo_path, width=1*inch, height=1*inch)
        logo.hAlign = 'CENTER'
        elements.append(logo)
    except Exception as e:
        pass  # If logo not found, skip it
    
    title_style = ParagraphStyle(
        name='TitleStyle',
        fontSize=20,
        leading=24,
        alignment=1,  # Center alignment
        textColor=colors.HexColor('#343A40'),
        spaceAfter=6
    )
    title = Paragraph("WSC - A Workstation Companion App", title_style)
    elements.append(title)
    
    subtitle_style = ParagraphStyle(
        name='SubtitleStyle',
        fontSize=16,
        leading=18,
        alignment=1,
        textColor=colors.HexColor('#6C757D'),
        spaceAfter=2
    )
    subtitle = Paragraph(
        "Simplify your radiology workflow with our intuitive and comprehensive tools.",
        subtitle_style
    )
    elements.append(subtitle)
    
    italic_text_style = ParagraphStyle(
        name='ItalicTextStyle',
        fontSize=14,
        leading=12,
        alignment=1,
        textColor=colors.HexColor('#28A745'),
        spaceAfter=12,
        italic=True
    )
    italic_text = Paragraph("Because every hero needs a trusty companion.", italic_text_style)
    elements.append(italic_text)
    
    # Document Title
    report_title_style = ParagraphStyle(
        name='ReportTitleStyle',
        fontSize=20,
        leading=24,
        alignment=1,
        textColor=colors.HexColor('#006400'),
        spaceAfter=6
    )
    report_title = Paragraph("Report Template", report_title_style)
    elements.append(report_title)
    
    template_name = data.get('template_name', '')
    template_name_style = ParagraphStyle(
        name='TemplateNameStyle',
        fontSize=14,
        leading=18,
        alignment=1,
        textColor=colors.HexColor('#6C757D'),
        spaceAfter=12
    )
    template_name_paragraph = Paragraph(template_name, template_name_style)
    elements.append(template_name_paragraph)
    
    # Patient Information Table
    patient_info_data = [
        ['Name:', data.get('name', 'No name provided'), 'Gender:', data.get('gender', 'Not specified')],
        ['ID:', data.get('patient_id', 'No ID provided'), 'Age:', data.get('age', 'Not specified')],
        ['DOB:', data.get('dob', 'Not specified'), 'Location:', data.get('location', 'No location provided')]
    ]
    
    table_style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
    ])
    
    patient_table = Table(patient_info_data, colWidths=[1*inch, 2.5*inch, 1*inch, 2.5*inch])
    patient_table.setStyle(table_style)
    elements.append(patient_table)
    elements.append(Spacer(1, 12))
    
    # Sections: Clinical Context, Protocol/Technique, Comparisons, Observations, Conclusions, Recommendations
    def add_section(heading, content):
        combined_style = ParagraphStyle(
        name='CombinedStyle',
        fontSize=12,
        leading=15,
        textColor=colors.black,
        spaceAfter=12,
        spaceBefore=12
        )
        combined_text = f'<b>{heading}</b> {content if content else "No information provided"}'
        elements.append(Paragraph(combined_text, combined_style))
        
        
    # Clinical Context
    add_section('Clinical Context:', data.get('clinical_info', 'No clinical information provided'))
    
    # Protocol/Technique
    add_section('Protocol/Technique:', data.get('technical_info', 'No technique information provided'))
    
    # Comparisons
    add_section('Comparisons:', data.get('comparison', 'No relevant priors available for comparison'))
    
    # Observations
    # setting styles for observation fields :
    
    # Section name in bold and blue color
    section_style = ParagraphStyle(
        name='SectionStyle',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0066CC'),
        spaceAfter=4
        )
    detail_style = ParagraphStyle(
        name='DetailStyle',
        fontSize=12,
        leading=15,
        leftIndent=20,
        spaceAfter=6
        )
    heading_style = ParagraphStyle(
        name='HeadingStyle',
        fontSize=14,
        leading=20,
        textColor=colors.black,
        spaceAfter=6,
        spaceBefore=12
    )
    elements.append(Paragraph('Observations:', heading_style))
    
    # Ensure observations is always a list, with a default entry if the list is empty or None
    
    observations = data.get('observations', [])  # Default to an empty list if observations is None
    section_name = ""
    detail = ""

    for obs in observations:
        if obs is None:  # Skip if the observation itself is None
            continue

        # Initialize defaults for each observation
        section_name = "Section"
        detail = "No details provided"
    
        for key, value in obs.items():
            if key == 'section':
                section_name = value if value else 'Section'  # Handle empty or None values
            elif key == 'details':
                detail = value if value else 'No details provided'  # Handle empty or None values

        # Add section and detail to the document
        section_paragraph = Paragraph(f"{section_name}:", section_style)
        elements.append(section_paragraph)
        detail_paragraph = Paragraph(detail, detail_style)
        elements.append(detail_paragraph)

    # Conclusions
    add_section('Conclusions:', data.get('conclusions', 'No conclusions provided'))
    
    # Recommendations
    add_section('Recommendations:', data.get('recommendations', 'No recommendations provided'))
    
    # Signature and Date
    signature_style = ParagraphStyle(
        name='SignatureStyle',
        fontSize=12,
        leading=15,
        spaceAfter=12,
        spaceBefore=36
    )
    registration_style=ParagraphStyle(
        name='RegistrationStyle',
        fontSize=12,
        leading=15,
        spaceAfter=12,
        spaceBefore=8,
        italic=True
    )
    signature_text = f"Reported and electronically signed by:                  "
    registration_no="Registration Number:               "
    signature_date = f"Dated: {datetime.now().strftime('%Y-%m-%d')}"
    elements.append(Paragraph(signature_text, signature_style))
    elements.append(Paragraph(registration_no, registration_style))
    elements.append(Paragraph(signature_date, signature_style))
    
    # Footer
    def add_footer(canvas, doc):
        footer_text = 'SmartReportTemplates\nBrought to you by WSCompanion: because every Hero needs a companion'
        canvas.saveState()
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(colors.HexColor('#6B8E23'))
        width, height = doc.pagesize
        footer_lines = footer_text.split('\n')
        y = 15 * mm
        for line in footer_lines:
            canvas.drawCentredString(width / 2.0, y, line)
            y -= 12  # Move up for next line
        canvas.restoreState()
    
    # Build the PDF
    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    
    buffer.seek(0)
    
    if return_path_only:
        # Save buffer to a temporary file
        temp_pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_pdf_file.write(buffer.getvalue())
        temp_pdf_file.close()
        return temp_pdf_file.name
    else:   
        # Return the buffer for direct download
        return buffer