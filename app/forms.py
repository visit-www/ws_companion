from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo

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
    file_type = StringField('File Type', validators=[DataRequired(), Length(max=10)])
    submit = SubmitField('Add Guideline')

class AddContentForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Add Content')

class AddRadiologyCalculatorForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Add Calculator')