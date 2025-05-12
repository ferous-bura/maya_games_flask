import random
import sqlite3
import logging
import time
from flask import request, jsonify, render_template
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash

from startapp import call_home
from utils import User, ensure_db_initialized, app
from constant import generate_user_token, send_telegram_notification

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@app.route('/bot/full_status', methods=['POST'])
def full_status():
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    if not telegram_id:
        logging.error("Missing telegram_id in full_status request")
        return jsonify({"status": "error", "message": "Telegram ID required."}), 400
    try:
        with sqlite3.connect('transactions.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute("SELECT username, deposit, language FROM users WHERE telegram_id = ?", (telegram_id,))
            user = c.fetchone()
            if not user:
                logging.info(f"User not found for telegram_id: {telegram_id}")
                return jsonify({"status": "not_found"}), 404
            c.execute("""
                SELECT transaction_number, amount, method, source, payer_name, payment_date, timestamp, status
                FROM transactions WHERE telegram_id = ?
            """, (telegram_id,))
            transactions = [
                {
                    "transaction_number": t[0],
                    "amount": t[1],
                    "method": t[2],
                    "source": t[3],
                    "payer_name": t[4],
                    "payment_date": t[5],
                    "timestamp": t[6],
                    "status": t[7]
                }
                for t in c.fetchall()
            ]
            logging.info(f"Full status for {telegram_id}: username={user[0]}, deposit={user[1]}, transactions={len(transactions)}")
            return jsonify({
                "username": user[0],
                "deposit": user[1],
                "language": user[2],
                "transactions": transactions,
                "game_activities": []
            }), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in full_status for {telegram_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/bot/register', methods=['POST'])
def register():
    data = request.get_json()
    required_fields = ['phone', 'username', 'full_name', 'telegram_id']
    if not all(field in data for field in required_fields):
        logging.error(f"Missing required fields in register: {data}")
        return jsonify({"status": "error", "message": "Missing required fields."}), 400

    phone = data['phone']
    username = data['username']
    full_name = data['full_name']
    telegram_id = data['telegram_id']
    language = 'en' # data['language']
    photo_url = data.get('photo_url')

    try:
        with sqlite3.connect('transactions.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE telegram_id = ? OR phone = ?", (telegram_id, phone))
            if c.fetchone():
                logging.info(f"User already exists: telegram_id={telegram_id}, phone={phone}")
                return jsonify({"status": "error", "message": "User already registered."}), 400

            c.execute("""
                INSERT INTO users (phone, username, full_name, telegram_id, language, photo_url, deposit)
                VALUES (?, ?, ?, ?, ?, ?, 0.0)
            """, (phone, username, full_name, telegram_id, language, photo_url))
            try:
                conn.commit()
            except sqlite3.Error as e:
                logging.error(f"Database commit error in register: {e}")
            logging.info(f"Registered user: telegram_id={telegram_id}, username={username}")
        return jsonify({"status": "success", "message": "User registered."}), 201
    except sqlite3.Error as e:
        logging.error(f"Database error in register: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/bot/notify', methods=['POST'])
def notify():
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    message = data.get('message')
    if not telegram_id or not message:
        return jsonify({"status": "error", "message": "Telegram ID and message required."}), 400
    return send_telegram_notification(telegram_id, message, "Notification sent.")

@app.route('/bot/generate_token', methods=['POST'])
def generate_token():
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    print(f'telegram id {telegram_id}')
    if not telegram_id:
        return jsonify({"status": "error", "message": "Telegram ID required."}), 400
    token = generate_user_token(telegram_id)
    if not token:
        return jsonify({"status": "error", "message": "Failed to generate token."}), 500
    return jsonify({"status": "success", "token": token}), 200

@app.route('/bot/check_transaction', methods=['POST'])
def check_transaction():
    data = request.get_json()
    transaction_number = data.get('transaction_number')
    telegram_id = data.get('telegram_id')
    if not transaction_number or not telegram_id:
        return jsonify({"status": "error", "message": "Transaction number and Telegram ID required."}), 400
    try:
        with sqlite3.connect('transactions.db') as conn:
            c = conn.cursor()
            c.execute("""
                SELECT amount, method, source, payer_name, payment_date, timestamp, verified, status
                FROM transactions 
                WHERE transaction_number = ? AND telegram_id = ?
            """, (transaction_number, telegram_id))
            transaction = c.fetchone()
            if not transaction:
                return jsonify({"status": "error", "message": "Transaction not found."}), 200
            amount, method, source, payer_name, payment_date, timestamp, verified, status = transaction
            message = f"{amount} ETB via {method} ({source}) on {payment_date or timestamp} ({status})"
            return jsonify({"status": "success", "message": message}), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in check_transaction: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/bot/check_registration', methods=['POST'])
def check_registration():
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    if not telegram_id:
        return jsonify({"status": "error", "message": "Telegram ID required."}), 400
    try:
        with sqlite3.connect('transactions.db') as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            if c.fetchone():
                return jsonify({"status": "registered"}), 200
            else:
                return jsonify({"status": "not_registered"}), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in check_registration: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        try:
            with sqlite3.connect('transactions.db') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, phone, username, password_hash, is_staff FROM users WHERE username = ?", (username,))
                user_data = cursor.fetchone()
                if user_data and check_password_hash(user_data[3], password):
                    user = User(user_data[0], user_data[1], user_data[2], user_data[3], user_data[4])
                    login_user(user)
                    logging.info(f"User {username} logged in")
                    return jsonify({"status": "success", "message": "Logged in successfully."}), 200
                else:
                    logging.warning(f"Failed login attempt for {username}")
                    return jsonify({"status": "error", "message": "Invalid credentials."}), 401
        except sqlite3.Error as e:
            logging.error(f"Database error in login: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    logging.info(f"User {username} logged out")
    return jsonify({"status": "success", "message": "Logged out successfully."}), 200

@app.route('/update_language', methods=['POST'])
def update_language():
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    language = data.get('language')
    if not all([telegram_id, language]) or language not in ['en', 'am']:
        return jsonify({"status": "error", "message": "Invalid telegram_id or language."}), 400
    try:
        with sqlite3.connect('transactions.db') as conn:
            c = conn.cursor()
            c.execute("UPDATE users SET language = ? WHERE telegram_id = ?", (language, telegram_id))
            if c.rowcount == 0:
                return jsonify({"status": "error", "message": "User not found."}), 404
            conn.commit()
            logging.info(f"Language updated for telegram_id={telegram_id} to {language}")
        return jsonify({"status": "success", "message": "Language updated."}), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in update_language: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def home():
    token = request.args.get('token')
    demo_mode = request.args.get('demo', 'false').lower() == 'true'
    if not token:
        return jsonify({"status": "error", "message": "Token required."}), 401

    try:
        with sqlite3.connect("transactions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, full_name, deposit, photo_url, telegram_id
                FROM users 
                WHERE bot_token = ? AND token_expiry > ?
            """, (token, int(time.time())))
            user = cursor.fetchone()
            if not user:
                return jsonify({"status": "error", "message": "Invalid or expired token."}), 401
            user_id, username, full_name, deposit, photo_url, telegram_id = user

            cursor.execute("""
                SELECT transaction_number, amount, method, source, payer_name, payment_date, timestamp
                FROM transactions
                WHERE telegram_id = ? AND verified = FALSE AND status = 'pending'
            """, (telegram_id,))
            pending_deposits = [
                {
                    "transaction_number": t[0],
                    "amount": t[1],
                    "method": t[2],
                    "source": t[3],
                    "payer_name": t[4],
                    "payment_date": t[5],
                    "timestamp": t[6]
                }
                for t in cursor.fetchall()
            ]

            cursor.execute("""
                SELECT game_type, amount_won, amount_lost, timestamp
                FROM game_activities
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 3
            """, (user_id,))
            recent_games = [
                {"game_type": g[0], "amount_won": g[1], "amount_lost": g[2], "timestamp": g[3]}
                for g in cursor.fetchall()
            ]

            cursor.execute("""
                SELECT u.username, g.amount_won, g.game_type, g.timestamp
                FROM game_activities g
                JOIN users u ON g.user_id = u.id
                WHERE g.amount_won > 0
                ORDER BY g.timestamp DESC
                LIMIT 5
            """)
            leaderboard = [
                {"username": u[0][:3] + "***", "amount_won": u[1], "game_type": u[2], "timestamp": u[3]}
                for u in cursor.fetchall()
            ]

        display_name = full_name or username
        photo_url = photo_url or "/static/default_user.jpg"
        greetings = [
            f"Hello, {display_name}! 👋",
            f"Back for more fun, {display_name}?",
            f"Ready to win, {display_name}?",
            f"Great to see you, {display_name}!"
        ]
        greeting = random.choice(greetings)

        return render_template(
            'hom.html',
            user_id=user_id,
            username=display_name,
            deposit_balance=deposit,
            photo_url=photo_url,
            demo_mode=demo_mode,
            recent_games=recent_games,
            is_new_user=len(recent_games) == 0,
            greeting=greeting,
            leaderboard=leaderboard,
            pending_deposits=pending_deposits
        )

    except sqlite3.Error as e:
        logging.error(f"Database error in home: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/ping')
def ping():
    return "Ping successful!"

if __name__ == '__main__':
    call_home()
    ensure_db_initialized()
    app.run(host='0.0.0.0', port=5000, debug=True)
