import sqlite3
import logging
import secrets
import time
from flask import Blueprint, Flask, send_from_directory
from flask_login import UserMixin

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Telegram bot token
TELEGRAM_BOT_TOKEN = '7637824158:AAGFSKHcHn2jxCoBlQ7sUulR8caeQYIUEtQ'

# Receipt Project API settings
RECEIPT_API_URL = "http://127.0.0.1:8000"
RECEIPT_API_KEY = "251f0f6ad923f82749b30a2ee1f378d1"

payment_blueprint = Blueprint('payment', __name__)

BaseUrl = "http://127.0.0.1:5000"

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
                source TEXT,
                payer_name TEXT,
                payment_date TEXT,
                sender TEXT,
                raw_message TEXT,
                timestamp TEXT,
                verified BOOLEAN DEFAULT FALSE,
                status TEXT DEFAULT 'pending',
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
                timestamp DATETIME,
                numbers TEXT,
                total_bets REAL DEFAULT 0.0,
                total_payouts REAL DEFAULT 0.0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referee_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                reward_issued BOOLEAN DEFAULT FALSE,
                reward_amount REAL DEFAULT 10.0,
                FOREIGN KEY (referrer_id) REFERENCES users(id),
                FOREIGN KEY (referee_id) REFERENCES users(id)
            )
        """)
        conn.commit()
    logging.info("Database initialized.")

def generate_user_token(telegram_id):
    """Generate a token for a user and store it in the database."""
    try:
        with sqlite3.connect('transactions.db') as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user = c.fetchone()
            if not user:
                logging.error(f"User not found for telegram_id: {telegram_id}")
                return None
            token = secrets.token_hex(16)
            expiry = int(time.time()) + 3600 * 24
            c.execute("UPDATE users SET bot_token = ?, token_expiry = ? WHERE telegram_id = ?", (token, expiry, telegram_id))
            conn.commit()
            logging.info(f"Generated token for telegram_id={telegram_id}")
            return token
    except sqlite3.Error as e:
        logging.error(f"Database error in generate_user_token: {e}")
        return None

def update_user_balance(user_id, amount):
    """Update user's deposit balance."""
    try:
        with sqlite3.connect('transactions.db') as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET deposit = deposit + ? WHERE id = ?", (amount, user_id))
            conn.commit()
            logging.info(f"Updated balance for user_id={user_id} by {amount} ETB")
    except sqlite3.Error as e:
        logging.error(f"Error updating balance for user_id={user_id}: {e}")
