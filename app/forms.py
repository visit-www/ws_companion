from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo, Optional, URL

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=150)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=150)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


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