from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, IntegerField,DateField,FloatField, FileField, FieldList, FormField
from wtforms.validators import DataRequired, Length, EqualTo, Optional, URL

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()], render_kw={"placeholder": "Enter Username", "class": "form-control"})
    password = PasswordField('Password', validators=[DataRequired()], render_kw={"placeholder": "Enter Password", "class": "form-control"})
    submit = SubmitField('Login', render_kw={"class": "btn btn-primary login-btn w-100"})
    remember = BooleanField('Remember Me')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=150)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class ObservationForm(FlaskForm):
    section = StringField('Section', validators=[Optional()])
    details = TextAreaField('Details', validators=[Optional()])

class AddReportTemplateMobile(FlaskForm):
    template_name = StringField('Template Name', validators=[DataRequired()])
    def validate_template_name(self, field):
        existing = db.session.query(UserReportTemplate).filter_by(
        template_name=field.data,
        user_id=current_user.id).first()
        if existing:
            raise ValidationError("A template with this name already exists.")
    # Patient Information
    name = StringField('Name', validators=[Optional()])
    gender = StringField('Gender', validators=[Optional()])
    patient_id = StringField('ID', validators=[Optional()])
    age = IntegerField('Age', validators=[Optional()])
    dob = DateField('DOB', validators=[Optional()])
    location = StringField('Location', validators=[Optional()])
    
    clinical_info = TextAreaField('Clinical Info', validators=[Optional()])
    technical_info = TextAreaField('Technique', validators=[Optional()])
    comparison = TextAreaField('Comparison', validators=[Optional()])
    
    # Observations Section (Dynamic fields)
    observations = FieldList(FormField(ObservationForm), min_entries=1)
    
    # Conclusions and Recommendations
    conclusions = TextAreaField('Conclusions', validators=[Optional()])
    recommendations = TextAreaField('Recommendations', validators=[Optional()])
    
    # Unique Submit Button
    submit_mobile = SubmitField('Save Report Template')

from wtforms import ValidationError
from app.models import UserReportTemplate
from flask_login import current_user
from app import db
class AddReportTemplateDesktop(FlaskForm):
    template_name = StringField('Template Name', validators=[DataRequired()])
    def validate_template_name(self, field):
        existing = db.session.query(UserReportTemplate).filter_by(
        template_name=field.data,
        user_id=current_user.id).first()
        if existing:
            raise ValidationError("A template with this name already exists.")
    
    # Patient Information
    name = StringField('Name', validators=[Optional()])
    gender = StringField('Gender', validators=[Optional()])
    patient_id = StringField('ID', validators=[Optional()])
    age = IntegerField('Age', validators=[Optional()])
    dob = DateField('DOB', validators=[Optional()])
    location = StringField('Location', validators=[Optional()])
    
    clinical_info = TextAreaField('Clinical Info', validators=[Optional()])
    technical_info = TextAreaField('Technique', validators=[Optional()])
    comparison = TextAreaField('Comparison', validators=[Optional()])
    
    # Observations Section (Dynamic fields)
    observations = FieldList(FormField(ObservationForm), min_entries=1)
    
    # Conclusions and Recommendations
    conclusions = TextAreaField('Conclusions', validators=[Optional()])
    recommendations = TextAreaField('Recommendations', validators=[Optional()])
    
    # Unique Submit Button
    submit_desktop = SubmitField('Save Report Template')
    
class AddGuidelineForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=500)])
    file_type = SelectField('File Type', choices=[
        ('pdf', 'PDF'),
        ('docx', 'DOCX'),
        ('html', 'HTML'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    file = FileField('File', validators=[Optional(), FileAllowed(['pdf', 'docx', 'html', 'txt'])])
    url = StringField('URL', validators=[Optional(), URL(), Length(max=256)])
    embed_code = TextAreaField('Embed Code', validators=[Optional()])
    submit = SubmitField('Add Guideline')

class AddUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=150)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=150)])
    is_admin = BooleanField('Is Admin')
    is_paid = BooleanField('Is Paid')
    submit = SubmitField('Add User')

class UploadForm(FlaskForm):
    file = FileField('Upload File', validators=[DataRequired()])
    submit = SubmitField('Upload File', render_kw={"class": "btn btn-primary btn-lg btn-block"})
    
class AddRadiologyCalculatorForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Add Calculator')
    
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, BooleanField, DateField,
    SelectField, FloatField, FileField, FieldList
)
from wtforms.validators import DataRequired, Optional
from flask_wtf.file import FileAllowed


class AddCPDLogForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    description = TextAreaField("Description", validators=[Optional()])
    reflection = TextAreaField("Reflection", validators=[Optional()])
    has_reflection = BooleanField("Include Reflection Bonus Point")

    start_date = DateField("Start Date", validators=[Optional()])
    end_date = DateField("End Date", validators=[Optional()])

    activity_type = SelectField(
        "Activity Type",
        coerce=int,
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )

    cpd_points_guideline = StringField("RCR Recommended Points", validators=[Optional()])
    cpd_points_claimed = FloatField("CPD Points Claimed", validators=[Optional()])

    certificate_files = FieldList(
        FileField(
            "Upload Certificate",
            validators=[FileAllowed(['docx', 'pdf', 'jpg', 'png', 'jpeg'], '❌ Only .docx, .pdf, .jpg, .png or .jpeg files are allowed.')]
        ),
        min_entries=3,
        label="Upload up to 3 certificates"
    )

    external_links = TextAreaField("External Links (one per line)", validators=[Optional()])
    tags = StringField("Tags", validators=[Optional()])
    notes = TextAreaField("Additional Notes", validators=[Optional()])