import sqlite3
import logging
import secrets
import time
from flask import Blueprint, Flask, redirect, render_template, request, jsonify
from flask_login import LoginManager, current_user

from utils import BaseUrl, generate_user_token

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

play_blueprint = Blueprint('play', __name__)

@play_blueprint.route('/', methods=['GET', 'POST'])
def play():
    """Redirect to homepage with a generated token for the user."""
    # Get telegram_id from query parameter, POST data, or logged-in user
    telegram_id = None
    if request.method == 'POST':
        data = request.get_json() or request.form
        telegram_id = data.get('telegram_id')
    else:
        telegram_id = request.args.get('telegram_id')
    
    # If user is logged in, use current_user.telegram_id
    if not telegram_id and current_user.is_authenticated:
        telegram_id = current_user.telegram_id

    if not telegram_id:
        logging.error("Missing telegram_id in play request")
        return jsonify({"status": "error", "message": "Telegram ID required."}), 400

    try:
        with sqlite3.connect('transactions.db') as conn:
            c = conn.cursor()
            c.execute("SELECT deposit FROM users WHERE telegram_id = ?", (telegram_id,))
            user = c.fetchone()
            if not user:
                logging.error(f"User not found for telegram_id: {telegram_id}")
                return jsonify({"status": "error", "message": "User not found."}), 404
            
            deposit = user[0]
            demo_mode = deposit <= 0

            # Generate token
            token = generate_user_token(telegram_id)
            if not token:
                logging.error(f"Failed to generate token for telegram_id: {telegram_id}")
                return jsonify({"status": "error", "message": "Failed to generate token."}), 500

            # Construct homepage URL
            web_app_url = f"{BaseUrl}/?token={token}&demo={demo_mode}"
            logging.info(f"Redirecting telegram_id={telegram_id} to {web_app_url}")
            
            return redirect(web_app_url)
            
    except sqlite3.Error as e:
        logging.error(f"Database error in play: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@play_blueprint.route('/<game_type>', methods=['GET'])
def play_game(game_type):
    valid_games = ['keno', 'spin', 'bingo', 'ludo']
    if game_type not in valid_games:
        logging.error(f"Invalid game type: {game_type}")
        return jsonify({"status": "error", "message": "Invalid game type."}), 400

    token = request.args.get('token')
    demo_mode = request.args.get('demo', 'false').lower() == 'true'

    if not token:
        logging.error("Missing token in play_game request")
        return jsonify({"status": "error", "message": "Token required."}), 401

    try:
        with sqlite3.connect('transactions.db', timeout=10) as conn:
            c = conn.cursor()
            current_time = int(time.time())
            c.execute("""
                SELECT id, username, deposit, photo_url 
                FROM users 
                WHERE bot_token = ? AND token_expiry > ?
            """, (token, current_time))
            user = c.fetchone()
            if not user:
                logging.error(f"Invalid or expired token: {token}")
                return jsonify({"status": "error", "message": "Invalid or expired token."}), 401
            user_id, username, deposit, photo_url = user

            if not demo_mode and deposit < 20:
                logging.info(f"Insufficient balance for user_id={user_id}, deposit={deposit} ETB")
                return jsonify({
                    "status": "error",
                    "message": "Insufficient balance. Minimum 20 ETB required. Use /deposit in Telegram."
                }), 403

            c.execute("""
                INSERT INTO game_activities (user_id, game_type, amount_won, amount_lost, is_paid, timestamp)
                VALUES (?, ?, 0.0, 0.0, ?, CURRENT_TIMESTAMP)
            """, (user_id, game_type, 0 if demo_mode else 1))
            conn.commit()
            logging.info(f"Started {game_type} for user_id={user_id}, demo_mode={demo_mode}")

            return render_template(
                f'{game_type}.html',
                game_type=game_type,
                username=username,
                deposit=deposit,
                photo_url=photo_url or '/static/default_user.jpg',
                demo_mode=demo_mode,
                token=token
            )

    except sqlite3.Error as e:
        logging.error(f"Database error in play_game: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
