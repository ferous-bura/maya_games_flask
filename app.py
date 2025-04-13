import threading
from flask import Flask, request, jsonify, render_template
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import requests
import logging
import secrets
import hashlib
import time
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Telegram bot token
TELEGRAM_BOT_TOKEN = '6993686742:AAEcsXlDoH57Tn5NSVpWns7zhbfpDYEllp0'

# Phone to Telegram ID mapping
PHONE_TO_TELEGRAM = {
    "+251911223344": 7831842753,
    "+251922334455": 5587470125
}

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, phone, username, password_hash, is_staff):
        self.id = id
        self.phone = phone
        self.username = username
        self.password_hash = password_hash
        self.is_staff = is_staff

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phone, username, password_hash, is_staff FROM users WHERE id = ?", (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            return User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4])
        return None

def init_db():
    logging.debug("Initializing the database...")
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE,
                username TEXT,
                deposit REAL DEFAULT 0.0,
                language TEXT DEFAULT 'en',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                password_hash TEXT,
                telegram_id INTEGER UNIQUE,
                bot_token TEXT,
                token_expiry INTEGER,
                is_staff BOOLEAN DEFAULT FALSE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                transaction_code TEXT,
                amount REAL,
                payment_method TEXT,
                total_deposit REAL,
                sender TEXT,
                raw_message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                game_type TEXT,
                amount_won REAL DEFAULT 0.0,
                amount_lost REAL DEFAULT 0.0,
                is_paid BOOLEAN DEFAULT FALSE,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
    logging.debug("Database initialized.")

init_db()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/ping')
def ping():
    return "Ping successful!"

@app.route('/bot/register', methods=['POST'])
def bot_register():
    data = request.get_json()
    phone = data.get('phone')
    username = data.get('username')
    first_name = data.get('first_name')
    telegram_id = data.get('telegram_id')
    language = data.get('language', 'en')

    if not all([phone, username, telegram_id]):
        logging.error("Missing registration data.")
        return jsonify({"status": "error", "message": "Phone, username, and telegram_id are required."}), 400

    try:
        with sqlite3.connect("transactions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (phone, username, language, telegram_id, is_staff)
                VALUES (?, ?, ?, ?, FALSE)
            """, (phone, username, language, telegram_id))
            conn.commit()
            logging.info(f"Bot user registered: {phone}, Telegram ID: {telegram_id}")
            return jsonify({"status": "success", "message": "Registration successful."}), 201
    except sqlite3.IntegrityError:
        logging.error(f"Duplicate phone or telegram_id: {phone}, {telegram_id}")
        return jsonify({"status": "error", "message": "Phone number or Telegram ID already registered."}), 400

@app.route('/bot/user_status', methods=['POST'])
def user_status():
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    if not telegram_id:
        return jsonify({"status": "error", "message": "Telegram ID required."}), 400

    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT deposit FROM users WHERE telegram_id = ?", (telegram_id,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"status": "error", "message": "User not found."}), 404
            return jsonify({"status": "success", "deposit": user[0]}), 200
        except sqlite3.OperationalError as e:
            logging.error(f"Database error: {e}")
            return jsonify({"status": "error", "message": "Database error occurred."}), 500

@app.route('/bot/generate_token', methods=['POST'])
def generate_token():
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    if not telegram_id:
        return jsonify({"status": "error", "message": "Telegram ID required."}), 400

    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, phone FROM users WHERE telegram_id = ?", (telegram_id,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"status": "error", "message": "User not found."}), 404

            user_id, phone = user
            token = secrets.token_hex(32)
            token_hash = hashlib.sha256(f"{token}{user_id}{phone}".encode()).hexdigest()
            expiry = int(time.time()) + 600  # 10-minute expiry

            cursor.execute("UPDATE users SET bot_token = ?, token_expiry = ? WHERE id = ?", 
                          (token_hash, expiry, user_id))
            conn.commit()

            return jsonify({"status": "success", "token": token_hash}), 200
        except sqlite3.OperationalError as e:
            logging.error(f"Database error: {e}")
            return jsonify({"status": "error", "message": "Database error occurred."}), 500

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if not current_user.is_staff:
        return jsonify({"status": "error", "message": "Staff access only."}), 403
    if request.method == 'POST':
        phone = request.form.get('phone')
        username = request.form.get('username')
        password = request.form.get('password')
        language = request.form.get('language', 'en')
        is_staff = request.form.get('is_staff', False, type=bool)

        if not all([phone, username, password]):
            return jsonify({"status": "error", "message": "All fields are required."}), 400

        password_hash = generate_password_hash(password)
        try:
            with sqlite3.connect("transactions.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (phone, username, password_hash, language, is_staff)
                    VALUES (?, ?, ?, ?, ?)
                """, (phone, username, password_hash, language, is_staff))
                conn.commit()
                return jsonify({"status": "success", "message": "Staff registered."}), 201
        except sqlite3.IntegrityError:
            return jsonify({"status": "error", "message": "Phone number already registered."}), 400
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')

        with sqlite3.connect("transactions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, phone, username, password_hash, is_staff FROM users WHERE phone = ?", (phone,))
            user_data = cursor.fetchone()

        if user_data and check_password_hash(user_data[3], password):
            user = User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4])
            if not user.is_staff:
                return jsonify({"status": "error", "message": "Staff access only."}), 403
            login_user(user)
            return jsonify({"status": "success", "message": "Login successful."}), 200
        return jsonify({"status": "error", "message": "Invalid credentials."}), 401
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({"status": "success", "message": "Logged out successfully."}), 200

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_staff:
        return jsonify({"status": "error", "message": "Staff access only."}), 403
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT phone, username, deposit, language FROM users WHERE id = ?", (current_user.id,))
        user_info = cursor.fetchone() or ('N/A', 'N/A', 0.0, 'en')
        cursor.execute("SELECT transaction_code, amount, payment_method, total_deposit, timestamp FROM transactions WHERE user_id = ?", (current_user.id,))
        transactions = cursor.fetchall()
        cursor.execute("SELECT game_type, amount_won, amount_lost, is_paid, timestamp FROM game_activities WHERE user_id = ?", (current_user.id,))
        game_activities = cursor.fetchall()

    return render_template('dashboard.html', 
                         user_info=user_info, 
                         transactions=transactions, 
                         game_activities=game_activities)

@app.route('/play/<game_type>', methods=['GET', 'POST'])
def play_game(game_type):
    if game_type not in ['keno', 'bingo', 'spin', 'ludo']:
        return jsonify({"status": "error", "message": "Invalid game type."}), 400

    token = request.args.get('token')
    demo_mode = request.args.get('demo', 'false').lower() == 'true'

    # Validate token
    if not token:
        return jsonify({"status": "error", "message": "Token required."}), 401
    current_time = int(time.time())
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, deposit FROM users WHERE bot_token = ? AND token_expiry > ?", 
                      (token, current_time))
        user = cursor.fetchone()
        if not user:
            return jsonify({"status": "error", "message": "Invalid or expired token."}), 401
        user_id, deposit = user

    if request.method == 'POST':
        if demo_mode:
            return jsonify({"status": "success", "message": "Demo play recorded.", 
                          "amount_won": 0, "amount_lost": 0}), 200

        bet_amount = float(request.form.get('bet_amount', 0))
        if bet_amount <= 0 or bet_amount > deposit:
            return jsonify({"status": "error", "message": "Invalid or insufficient bet amount."}), 400

        amount_won = 0
        amount_lost = bet_amount
        is_paid = False

        import random
        if game_type == 'keno':
            player_numbers = request.form.getlist('numbers', type=int)
            if len(player_numbers) != 10:
                return jsonify({"status": "error", "message": "Select exactly 10 numbers."}), 400
            drawn_numbers = random.sample(range(1, 81), 20)
            matches = len(set(player_numbers) & set(drawn_numbers))
            if matches >= 5:
                amount_won = bet_amount * (matches - 4)
                amount_lost = 0
                is_paid = True
        elif game_type == 'bingo':
            if random.random() > 0.7:
                amount_won = bet_amount * 3
                amount_lost = 0
                is_paid = True
        elif game_type == 'spin':
            outcomes = [0, 0.5, 1, 2, 5]
            multiplier = random.choice(outcomes)
            if multiplier > 0:
                amount_won = bet_amount * multiplier
                amount_lost = 0
                is_paid = True
        elif game_type == 'ludo':
            if random.random() > 0.6:
                amount_won = bet_amount * 2
                amount_lost = 0
                is_paid = True

        with sqlite3.connect("transactions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET deposit = deposit + ? - ? WHERE id = ?", 
                         (amount_won, amount_lost, user_id))
            cursor.execute("""
                INSERT INTO game_activities (user_id, game_type, amount_won, amount_lost, is_paid)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, game_type, amount_won, amount_lost, is_paid))
            conn.commit()

        return jsonify({
            "status": "success",
            "message": f"Played {game_type}",
            "amount_won": amount_won,
            "amount_lost": amount_lost,
            "details": {
                "keno": {"matches": matches, "drawn_numbers": drawn_numbers} if game_type == 'keno' else {},
                "spin": {"multiplier": multiplier} if game_type == 'spin' else {}
            }
        }), 200

    # return render_template(f'{game_type}.html', deposit=deposit, demo_mode=demo_mode)
    return render_template(f"{game_type}.html", user_id=user_id, deposit=deposit, demo=demo_mode)

@app.route('/payment', methods=['POST'])
@login_required
def payment():
    if not current_user.is_staff:
        return jsonify({"status": "error", "message": "Staff access only."}), 403
    data = request.get_json()
    transaction_code = data.get('transaction_code')
    amount = float(data.get('amount', 0))
    payment_method = data.get('payment_method', 'unknown')
    sender = data.get('sender')
    raw_message = data.get('raw_message')

    if not transaction_code or amount <= 0:
        return jsonify({"status": "error", "message": "Invalid transaction data."}), 400

    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET deposit = deposit + ? WHERE id = ?", (amount, current_user.id))
        cursor.execute("SELECT deposit FROM users WHERE id = ?", (current_user.id,))
        total_deposit = cursor.fetchone()[0]
        cursor.execute("""
            INSERT INTO transactions (user_id, transaction_code, amount, payment_method, total_deposit, sender, raw_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (current_user.id, transaction_code, amount, payment_method, total_deposit, sender, raw_message))
        conn.commit()

    if current_user.phone in PHONE_TO_TELEGRAM:
        chat_id = PHONE_TO_TELEGRAM[current_user.phone]
        msg = f"✅ Payment received!\nAmount: {amount} ETB\nTransaction: {transaction_code}"
        send_telegram_message(chat_id, msg)

    return jsonify({"status": "success", "message": f"Payment processed for {current_user.phone}"}), 200

@app.route('/process_payment', methods=['POST'])
def process_payment():
    data = request.get_json()
    transaction_number = data.get('transaction_number')
    amount = float(data.get('amount', 0))
    sender = data.get('sender')
    raw_message = data.get('raw_message')
    token = data.get('token')
    payment_method = data.get('payment_method', 'unknown')

    if not all([transaction_number, amount > 0, token]):
        return jsonify({"status": "error", "message": "Invalid transaction data or token."}), 400

    current_time = int(time.time())
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, deposit FROM users WHERE bot_token = ? AND token_expiry > ?", 
                      (token, current_time))
        user = cursor.fetchone()
        if not user:
            return jsonify({"status": "error", "message": "Invalid or expired token."}), 401

        user_id, deposit = user
        total_deposit = deposit + amount
        cursor.execute(
            """
            INSERT INTO transactions (user_id, transaction_code, amount, payment_method, total_deposit, sender, raw_message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (user_id, transaction_number, amount, payment_method, total_deposit, sender, raw_message)
        )
        cursor.execute("UPDATE users SET deposit = ? WHERE id = ?", (total_deposit, user_id))
        conn.commit()

    return jsonify({"status": "success", "message": "Payment processed successfully."}), 200

@app.route('/check_transaction', methods=['POST'])
def check_transaction():
    data = request.get_json()
    transaction_number = data.get('transaction_number')
    token = data.get('token')

    if not all([transaction_number, token]):
        return jsonify({"status": "error", "message": "Transaction number and token required."}), 400

    current_time = int(time.time())
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE bot_token = ? AND token_expiry > ?", 
                      (token, current_time))
        user = cursor.fetchone()
        if not user:
            return jsonify({"status": "error", "message": "Invalid or expired token."}), 401
        user_id = user[0]

        cursor.execute(
            """
            SELECT amount, total_deposit FROM transactions WHERE transaction_code = ? AND user_id = ?
            """,
            (transaction_number, user_id)
        )
        result = cursor.fetchone()

    if result:
        amount, total_deposit = result
        return jsonify({
            "status": "success",
            "message": f"{amount} ETB deposited, Total Deposit: {total_deposit} ETB"
        }), 200
    else:
        return jsonify({"status": "error", "message": "Transaction not found."}), 404

@app.route('/bot/update_phone', methods=['POST'])
def update_phone():
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    phone = data.get('phone')
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET phone = ? WHERE telegram_id = ?", (phone, telegram_id))
        conn.commit()
    return jsonify({"status": "success", "message": "Phone updated."}), 200

@app.route('/game_activity', methods=['POST'])
def game_activity():
    data = request.get_json()
    user_id = data.get('user_id')
    game_type = data.get('game_type')
    amount_won = data.get('amount_won', 0.0)
    amount_lost = data.get('amount_lost', 0.0)
    is_paid = data.get('is_paid', False)
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO game_activities (user_id, game_type, amount_won, amount_lost, is_paid)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, game_type, amount_won, amount_lost, is_paid))
        if is_paid:
            cursor.execute("UPDATE users SET deposit = deposit + ? - ? WHERE id = ?",
                          (amount_won, amount_lost, user_id))
        conn.commit()
    return jsonify({"status": "success"}), 200

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        r = requests.post(url, json=payload)
        logging.debug(f"Telegram response: {r.status_code}, {r.text}")
    except requests.RequestException as e:
        logging.error(f"Failed to send Telegram message: {e}")

def run_flask():
    logging.debug("Starting Flask server...")
    app.run(debug=False, host="0.0.0.0", use_reloader=False)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    flask_thread.join()