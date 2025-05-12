import sqlite3
import logging
import secrets
import time
from flask import Blueprint, Flask, send_from_directory
from flask_login import LoginManager, UserMixin
from src.bingo import bingo_blueprint
from src.play_game import play_blueprint
from src.payment import payment_blueprint
from src.keno import keno_blueprint
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Register blueprints
app.register_blueprint(bingo_blueprint, url_prefix='/bingo')
app.register_blueprint(keno_blueprint, url_prefix='/keno')
app.register_blueprint(play_blueprint, url_prefix='/play')
app.register_blueprint(payment_blueprint, url_prefix='/payment')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

payment_blueprint = Blueprint('payment', __name__)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, phone, username, password_hash, is_staff, telegram_id):
        self.id = id
        self.phone = phone
        self.username = username
        self.password_hash = password_hash
        self.is_staff = is_staff
        self.telegram_id = telegram_id

    def get_id(self):
        return str(self.id)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

def ensure_db_initialized():
    try:
        with sqlite3.connect("transactions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users LIMIT 1")
    except sqlite3.OperationalError:
        logging.info("Database or users table missing. Initializing...")
        init_db()

def update_game_activities_schema():
    try:
        with sqlite3.connect('transactions.db') as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(game_activities)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'hits' not in columns:
                cursor.execute("ALTER TABLE game_activities ADD COLUMN hits INTEGER DEFAULT 0")
                conn.commit()
                logging.info("Added `hits` column to `game_activities` table.")
    except sqlite3.Error as e:
        logging.error(f"Error adding `hits` column: {e}")

update_game_activities_schema()

def init_db():
    logging.info("Initializing the database...")
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE,
                username TEXT,
                full_name TEXT,
                photo_url TEXT,
                deposit REAL DEFAULT 0.0,
                language TEXT DEFAULT 'en',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                password_hash TEXT,
                telegram_id TEXT UNIQUE,
                bot_token TEXT,
                token_expiry INTEGER,
                is_staff BOOLEAN DEFAULT FALSE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                telegram_id TEXT,
                transaction_number TEXT UNIQUE,
                amount REAL,
                method TEXT,
                source TEXT,  -- telebirr, boa, cbe, manual
                payer_name TEXT,
                payment_date TEXT,
                sender TEXT,
                raw_message TEXT,
                timestamp TEXT,
                verified BOOLEAN DEFAULT FALSE,
                status TEXT DEFAULT 'pending',  -- pending, verified, rejected
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                game_type TEXT,
                odd_type TEXT,
                amount_won REAL DEFAULT 0.0,
                amount_lost REAL DEFAULT 0.0,
                is_paid BOOLEAN DEFAULT FALSE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                round_id TEXT,
                numbers TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keno_rounds (
                round_id TEXT PRIMARY KEY,
                timestamp DATETIME,
                numbers TEXT,
                stake REAL DEFAULT 0.0,
                total_bets REAL DEFAULT 0.0,
                total_payouts REAL DEFAULT 0.0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bingo_rounds (
                round_id TEXT PRIMARY KEY,
                stake TEXT,
                timestamp DATETIME,
                numbers TEXT,
                total_bets REAL DEFAULT 0.0,
                total_payouts REAL DEFAULT 0.0,
                status TEXT DEFAULT 'pending',  -- pending, active, completed
                FOREIGN KEY (stake) REFERENCES bingo_stakes(stake)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bingo_stakes (
                stake TEXT PRIMARY KEY,
                description TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bingo_cartella_selections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                round_id TEXT,
                user_id INTEGER,
                cartella_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (round_id) REFERENCES bingo_rounds(round_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        # Insert default stakes
        stakes = [
            ('10', '10 ETB Stake'),
            ('20', '20 ETB Stake'),
            ('50', '50 ETB Stake'),
            ('100', '100 ETB Stake'),
            ('practice', 'Practice Mode')
        ]
        cursor.executemany("INSERT OR IGNORE INTO bingo_stakes (stake, description) VALUES (?, ?)", stakes)
        conn.commit()
    logging.info("Database initialized.")

@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phone, username, password_hash, is_staff, telegram_id FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            return User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4], user_data[5])
        return None

def add_round_id_to_game_activities():
    try:
        with sqlite3.connect('transactions.db') as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(game_activities)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'round_id' not in columns:
                cursor.execute("ALTER TABLE game_activities ADD COLUMN round_id TEXT")
                conn.commit()
                print("Added `round_id` column to `game_activities` table.")
    except sqlite3.Error as e:
        print(f"Error adding `round_id` column: {e}")

def add_numbers_to_game_activities():
    try:
        with sqlite3.connect('transactions.db') as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(game_activities)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'numbers' not in columns:
                cursor.execute("ALTER TABLE game_activities ADD COLUMN numbers TEXT")
                conn.commit()
                print("Added `numbers` column to `game_activities` table.")
    except sqlite3.Error as e:
        print(f"Error adding `numbers` column: {e}")

add_round_id_to_game_activities()
add_numbers_to_game_activities()