import sqlite3
from flask import jsonify, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField
from wtforms.validators import DataRequired
import logging

import app as app

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app.app)
login_manager.login_view = 'login'

# User model for Flask-Login
class User(UserMixin):
    def __init__(self, id, phone, username, password_hash):
        self.id = id
        self.phone = phone
        self.username = username
        self.password_hash = password_hash

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phone, username, password_hash FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            return User(user_data[0], user_data[1], user_data[2], user_data[3])
        return None

# Check if password_hash column exists before adding
def update_users_table():
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'password_hash' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            logging.debug("Added password_hash column to users table.")

update_users_table()

# Forms for CSRF protection
class RegisterForm(FlaskForm):
    phone = StringField('Phone', validators=[DataRequired()])
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    language = SelectField('Language', choices=[('en', 'English'), ('am', 'Amharic')], default='en')

class LoginForm(FlaskForm):
    phone = StringField('Phone', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

@app.app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        phone = form.phone.data
        username = form.username.data
        password = form.password.data
        language = form.language.data

        password_hash = generate_password_hash(password)
        try:
            with sqlite3.connect("transactions.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (phone, username, password_hash, language)
                    VALUES (?, ?, ?, ?)
                """, (phone, username, password_hash, language))
                conn.commit()
                user_id = cursor.lastrowid
                user = User(user_id, phone, username, password_hash)
                login_user(user)
                logging.info(f"User registered: {phone}")
                return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            logging.error(f"Phone number already registered: {phone}")
            return jsonify({"status": "error", "message": "Phone number already registered."}), 400
    return render_template('templates/register.html', form=form)

@app.app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        phone = form.phone.data
        password = form.password.data

        with sqlite3.connect("transactions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, phone, username, password_hash FROM users WHERE phone = ?", (phone,))
            user_data = cursor.fetchone()

        if user_data and check_password_hash(user_data[3], password):
            user = User(user_data[0], user_data[1], user_data[2], user_data[3])
            login_user(user)
            logging.info(f"User logged in: {phone}")
            return redirect(url_for('dashboard'))
        logging.warning(f"Invalid login attempt: {phone}")
        return jsonify({"status": "error", "message": "Invalid credentials."}), 401
    return render_template('templates/login.html', form=form)

@app.app.route('/logout')
@login_required
def logout():
    logging.info(f"User logged out: {current_user.phone}")
    logout_user()
    return redirect(url_for('home'))

@app.app.route('/dashboard')
@login_required
def dashboard():
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT phone, username, deposit, language FROM users WHERE id = ?", (current_user.id,))
        user_info = cursor.fetchone() or ('N/A', 'N/A', 0.0, 'en')
        cursor.execute("SELECT transaction_code, amount, payment_method, total_deposit, timestamp FROM transactions WHERE user_id = ?", (current_user.id,))
        transactions = cursor.fetchall()
        cursor.execute("SELECT game_type, amount_won, amount_lost, is_paid, timestamp FROM game_activities WHERE user_id = ?", (current_user.id,))
        game_activities = cursor.fetchall()

    return render_template('templates/dashboard.html', 
                         user_info=user_info, 
                         transactions=transactions, 
                         game_activities=game_activities)