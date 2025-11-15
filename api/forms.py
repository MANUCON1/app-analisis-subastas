from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class RegisterForm(FlaskForm):
    username = StringField('Nombre de usuario', 
                          validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', 
                       validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', 
                            validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirmar contraseña', 
                                    validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registrarse')

class LoginForm(FlaskForm):
    email = StringField('Email', 
                       validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', 
                            validators=[DataRequired()])
    remember = BooleanField('Recordarme')
    submit = SubmitField('Iniciar sesión')
