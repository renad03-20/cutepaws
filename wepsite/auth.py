from flask import Blueprint, render_template, request, flash, redirect, url_for
import re
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from flask_login import login_user, login_required, logout_user, current_user


auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first() #check if the email user entered matchs an email in the database 
        if user: #if so ...
            if check_password_hash(user.password, password): # check if user enterd the same password in the database
                flash('logged in successfylly', category='success')
                login_user(user, remember= True )
                return redirect(url_for('views.home'))
            else:
                flash('invalid password', category='error')
        else:
            flash('envaild email', category='error')
             
    return render_template('login.html', user=current_user)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth.route('/signup', methods=['GET', 'POST'])
def sign_up():
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1') 
        password2 = request.form.get('password2')

        email_pattern = r"[^@]+@[^@]+\.[^@]+"
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$"

        user = User.query.filter_by(email=email).first()
        if user:
            flash('this email already exist', category='error')
        elif not re.match(email_pattern, email):
            flash('Invalid email address', category='error')
        elif len(first_name) < 2 or not first_name.isalpha():
            flash('First name must be at least 2 characters and only letters', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match', category='error')
        elif not re.match(password_pattern, password1):
            flash('Password must be at least 8 characters, include uppercase, lowercase, number, and special character', category='error')
        else:
            # You would hash the password and add the user to the DB here
            new_user = User(email= email, first_name= first_name, password= generate_password_hash(password1))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember= True )
            flash('congrats Account created successfully!', category='success')
            return redirect(url_for('views.home'))

    return render_template('signUp.html', user=current_user)