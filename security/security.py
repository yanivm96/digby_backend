# Form definitions for user with flask-security

from flask_security import RegisterForm
from markupsafe import Markup
from wtforms import StringField, BooleanField, PasswordField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired
from flask_wtf import FlaskForm

class ExtendedRegisterForm(RegisterForm):
    name = StringField('Full Name', [DataRequired()])
    address = StringField('Institutional Address', [DataRequired()])
    accepted_terms = BooleanField(Markup('I accept the <a href="/render_page/privacy_statement.html" target="_blank">Privacy</a> and <a href="/render_page/licensing_statement.html" target="_blank">Licensing</a> statements'))


class ProfileForm(FlaskForm):
    name = StringField('Full Name', [DataRequired()])
    address = StringField('Institutional Address', [DataRequired()])
    phone = StringField('Preferred telephone number', [DataRequired()])


def save_Profile(db, object, form, new=False):
    object.name = form.name.data
    object.address = form.address.data
    object.phone = form.phone.data

    if new:
        db.session.add(object)

    db.session.commit()


class FirstAccountForm(FlaskForm):
    name = StringField('Full Name', [DataRequired()])
    email = EmailField('Email', [DataRequired()])
    password = PasswordField('Password', [DataRequired()])

