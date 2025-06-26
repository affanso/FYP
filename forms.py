from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField, validators
import re

# Custom password validator
def validate_password(form, field):
    password = field.data
    if not re.search(r'[A-Z]', password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', password) or not re.search(r'[0-9]', password):
        raise validators.ValidationError('Password must have at least one capital letter, one special character, and one number.')


class RegistrationForm(FlaskForm):
    username = StringField(label='Username', validators=[validators.DataRequired()])
    email = EmailField(label='Email address', validators=[validators.DataRequired(), validators.Email()])
    password = PasswordField(
        label='Password',
        validators=[
            validators.DataRequired(),
            validators.Length(min=8, message="Password must be at least 8 characters long."),
            validate_password
        ]
    )
    confirm = PasswordField(
        label='Confirm password',
        validators=[
            validators.DataRequired(),
            validators.EqualTo('password', message='Passwords must match')
        ]
    )
    submit = SubmitField('Create Account')

class LoginForm(FlaskForm):
    email = EmailField(label='Email address', validators=[validators.DataRequired(), validators.Email()])
    password = PasswordField(label='Password', validators=[validators.DataRequired()])
    submit = SubmitField('Sign In')
