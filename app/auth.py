from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from flask_login import login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import login_manager
from flask_babel import lazy_gettext as _l
import os

# Authentication blueprint
auth = Blueprint('auth', __name__)

# Simple user model for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

# Demo user (to be replaced with a database)
users = {
    1: User(1, 'admin', generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'password')))
}

@login_manager.user_loader
def load_user(user_id):
    return users.get(int(user_id))

# Login form
class LoginForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    password = PasswordField(_l('Password'), validators=[DataRequired()])
    submit = SubmitField(_l('Login'))

# Login route
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        
        # Search for the user by username
        user = next((u for u in users.values() if u.username == username), None)
        
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=True)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        
        flash(_l('Incorrect username or password.'))
    
    return render_template('login.html', form=form)

# Logout route
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))