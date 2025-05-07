import sqlite3
import requests
import logging
import time
from flask import Blueprint, request, jsonify
from datetime import datetime, timezone

from utils import BaseUrl
BINGO_RTP = 0.92

# Add logging configuration
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

bingo_blueprint = Blueprint('bingo', __name__)

@bingo_blueprint.route('/current_round', methods=['GET'])
def bingo_current_round():
    """Fetch the current Bingo round details."""
    try:
        with sqlite3.connect('transactions.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT round_id, timestamp, numbers
                FROM bingo_rounds
                WHERE timestamp <= ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (datetime.now(timezone.utc),))
            round_data = cursor.fetchone()
            if not round_data:
                return jsonify({"status": "error", "message": "No active round found."}), 404

            round_id, timestamp, numbers = round_data
            numbers = eval(numbers)  # List of [letter, number]
            timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f%z')
            seconds_since_start = (datetime.now(timezone.utc) - timestamp).total_seconds()

            return jsonify({
                "status": "success",
                "round_id": round_id,
                "timestamp": timestamp.isoformat(),
                "numbers": numbers,
                "seconds_elapsed": seconds_since_start
            }), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in bingo_current_round: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@bingo_blueprint.route('/place_bet', methods=['POST'])
def bingo_place_bet():
    """Place a Bingo bet and calculate winnings."""
    data = request.get_json()
    logging.debug(f"Received request data: {data}")
    token = data.get('token')
    cartella_ids = data.get('cartella_ids')  # List of cartella numbers
    bet_amount = data.get('bet_amount')
    pattern_type = data.get('pattern_type')
    round_id = data.get('round_id')

    if not all([token, cartella_ids, bet_amount, pattern_type, round_id]) or len(cartella_ids) > 2:
        logging.warning("Invalid request data received.")
        return jsonify({"status": "error", "message": "Invalid request data."}), 400

    try:
        with sqlite3.connect('transactions.db', timeout=10) as conn:
            cursor = conn.cursor()
            logging.debug("Connected to the database.")
            cursor.execute("""
                SELECT id, deposit, telegram_id
                FROM users 
                WHERE bot_token = ? AND token_expiry > ?
            """, (token, int(time.time())))
            user = cursor.fetchone()
            if not user:
                logging.warning("Invalid or expired token.")
                return jsonify({"status": "error", "message": "Invalid or expired token."}), 401
            user_id, deposit, telegram_id = user

            total_bet = bet_amount * len(cartella_ids)
            if deposit < total_bet:
                logging.warning("Insufficient balance for user.")
                return jsonify({"status": "error", "message": "Insufficient balance."}), 403

            # Fetch round results
            cursor.execute("SELECT numbers, total_bets, total_payouts FROM bingo_rounds WHERE round_id = ?", (round_id,))
            round_data = cursor.fetchone()
            if not round_data:
                logging.warning("Round not found.")
                return jsonify({"status": "error", "message": "Round not found."}), 404
            called_numbers = eval(round_data[0])  # List of [letter, number]
            total_bets, total_payouts = round_data[1], round_data[2]

            # Simulate cartella check (server-side pattern checking would be ideal)
            required_patterns = 1 if pattern_type == 'single' else 2
            winnings = 0
            if len(called_numbers) >= 4:  # Minimum draws for a win
                winnings = total_bet * (5 if pattern_type == 'single' else 10) * BINGO_RTP

            # Update user balance and round stats
            cursor.execute("UPDATE users SET deposit = deposit - ? + ? WHERE id = ?", (total_bet, winnings, user_id))
            cursor.execute("""
                UPDATE bingo_rounds 
                SET total_bets = total_bets + ?, total_payouts = total_payouts + ?
                WHERE round_id = ?
            """, (total_bet, winnings, round_id))
            cursor.execute("""
                INSERT INTO game_activities (user_id, game_type, amount_won, amount_lost, is_paid, round_id)
                VALUES (?, 'bingo', ?, ?, TRUE, ?)
            """, (user_id, winnings, total_bet, round_id))
            conn.commit()

            logging.info(f"Bet placed successfully for user_id={user_id}, winnings={winnings}, new_balance={deposit - total_bet + winnings}")

            # Notify user
            if winnings > 0:
                requests.post(
                    f"{BaseUrl}/notify",
                    json={
                        "telegram_id": telegram_id,
                        "message": f"🎉 Bingo Round {round_id}: You won {winnings:.2f} ETB! New balance: {deposit - total_bet + winnings:.2f} ETB."
                    },
                    timeout=5
                )

            return jsonify({
                "status": "success",
                "winnings": winnings,
                "new_balance": deposit - total_bet + winnings
            }), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in bingo_place_bet: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
