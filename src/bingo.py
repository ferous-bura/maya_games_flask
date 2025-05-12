from flask import Blueprint, Flask, render_template, request, jsonify
import time
import sqlite3
import logging
import requests
from datetime import datetime, timezone
from constant import BaseUrl


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
BINGO_RTP = 0.92
STAKES = ['10', '20', '50', '100', 'practice']
ROUND_DURATION = 60  # seconds
NUMBERS_PER_ROUND = 75

bingo_blueprint = Blueprint('bingo', __name__)
app = bingo_blueprint

# Helper Functions
def get_current_round(stake):
    try:
        with sqlite3.connect('transactions.db', timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT round_id, timestamp, numbers, status
                FROM bingo_rounds
                WHERE stake = ? AND status IN ('pending', 'active')
                ORDER BY timestamp DESC
                LIMIT 1
            """, (stake,))
            round_data = cursor.fetchone()
            if round_data:
                round_id, timestamp, numbers, status = round_data
                numbers = eval(numbers) if numbers else []
                timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f%z')
                return round_id, timestamp, numbers, status
            # Create a new round if none exists
            round_id = f"round_{stake}_{int(time.time())}"
            timestamp = datetime.now(timezone.utc)
            cursor.execute("""
                INSERT INTO bingo_rounds (round_id, stake, timestamp, numbers, status)
                VALUES (?, ?, ?, ?, 'pending')
            """, (round_id, stake, timestamp.strftime('%Y-%m-%d %H:%M:%S.%f%z'), str([])))
            conn.commit()
            return round_id, timestamp, [], 'pending'
    except sqlite3.Error as e:
        logging.error(f"Database error in get_current_round: {e}")
        return None, None, None, None

# Join a stake group
@app.route('/join_stake', methods=['POST'])
def join_stake():
    data = request.get_json()
    stake = str(data.get('stake'))
    token = data.get('token')

    if stake not in STAKES:
        return jsonify({"status": "error", "message": "Invalid stake"}), 400
    if not token:
        return jsonify({"status": "error", "message": "Token required"}), 401

    try:
        with sqlite3.connect('transactions.db', timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, telegram_id
                FROM users 
                WHERE bot_token = ? AND token_expiry > ?
            """, (token, int(time.time())))
            user = cursor.fetchone()
            if not user:
                return jsonify({"status": "error", "message": "Invalid or expired token"}), 401
            user_id, telegram_id = user

            # Get current round
            round_id, _, _, _ = get_current_round(stake)
            if not round_id:
                return jsonify({"status": "error", "message": "Failed to get or create round"}), 500

            # Get available cartellas
            cursor.execute("""
                SELECT cartella_id
                FROM bingo_cartella_selections
                WHERE round_id = ?
            """, (round_id,))
            taken_cartellas = [row[0] for row in cursor.fetchall()]
            available_cartellas = [i for i in range(1, 101) if i not in taken_cartellas]

            # Get cartellas selected by this user
            cursor.execute("""
                SELECT cartella_id
                FROM bingo_cartella_selections
                WHERE round_id = ? AND user_id = ?
            """, (round_id, user_id))
            selected_cartellas = [row[0] for row in cursor.fetchall()]

            return jsonify({
                "status": "success",
                "user_id": user_id,
                "telegram_id": telegram_id,
                "available_cartellas": available_cartellas,
                "selected_cartellas": selected_cartellas,
                "round_id": round_id
            }), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in join_stake: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Select cartellas
@app.route('/select_cartellas', methods=['POST'])
def select_cartellas():
    data = request.get_json()
    stake = str(data.get('stake'))
    token = data.get('token')
    cartellas = data.get('cartellas', [])

    if stake not in STAKES:
        return jsonify({"status": "error", "message": "Invalid stake"}), 400
    if not token:
        return jsonify({"status": "error", "message": "Token required"}), 401
    if len(cartellas) > 2:
        return jsonify({"status": "error", "message": "Maximum 2 cartellas allowed"}), 400

    try:
        with sqlite3.connect('transactions.db', timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id
                FROM users 
                WHERE bot_token = ? AND token_expiry > ?
            """, (token, int(time.time())))
            user = cursor.fetchone()
            if not user:
                return jsonify({"status": "error", "message": "Invalid or expired token"}), 401
            user_id = user[0]

            # Get current round
            round_id, timestamp, numbers, status = get_current_round(stake)
            if not round_id:
                return jsonify({"status": "error", "message": "Failed to get or create round"}), 500

            # Check already selected cartellas
            cursor.execute("""
                SELECT cartella_id
                FROM bingo_cartella_selections
                WHERE round_id = ?
            """, (round_id,))
            taken_cartellas = set(row[0] for row in cursor.fetchall())

            # Validate cartellas
            for cartella in cartellas:
                if cartella in taken_cartellas:
                    return jsonify({"status": "error", "message": f"Cartella {cartella} is already taken"}), 400

            # Remove previous selections by this user
            cursor.execute("""
                DELETE FROM bingo_cartella_selections
                WHERE round_id = ? AND user_id = ?
            """, (round_id, user_id))

            # Insert new selections
            for cartella in cartellas:
                cursor.execute("""
                    INSERT INTO bingo_cartella_selections (round_id, user_id, cartella_id)
                    VALUES (?, ?, ?)
                """, (round_id, user_id, cartella))

            # Check if round should start (10 cartellas)
            cursor.execute("""
                SELECT COUNT(*) FROM bingo_cartella_selections WHERE round_id = ?
            """, (round_id,))
            total_cartellas = cursor.fetchone()[0]

            if total_cartellas >= 10 and status == 'pending':
                cursor.execute("""
                    UPDATE bingo_rounds
                    SET status = 'active'
                    WHERE round_id = ?
                """, (round_id,))
                status = 'active'

            conn.commit()

            return jsonify({
                "status": "success",
                "selected_cartellas": cartellas,
                "total_cartellas": total_cartellas,
                "game_status": status
            }), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in select_cartellas: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Start game
@app.route('/start', methods=['POST'])
def start_game():
    data = request.get_json()
    stake = str(data.get('stake'))
    token = data.get('token')
    cartella_ids = data.get('cartella_ids', [])

    if stake not in STAKES:
        return jsonify({"status": "error", "message": "Invalid stake"}), 400
    if not token:
        return jsonify({"status": "error", "message": "Token required"}), 401

    try:
        with sqlite3.connect('transactions.db', timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, deposit
                FROM users 
                WHERE bot_token = ? AND token_expiry > ?
            """, (token, int(time.time())))
            user = cursor.fetchone()
            if not user:
                return jsonify({"status": "error", "message": "Invalid or expired token"}), 401
            user_id, deposit = user

            # Get current round
            round_id, timestamp, numbers, status = get_current_round(stake)
            if not round_id:
                return jsonify({"status": "error", "message": "Failed to get or create round"}), 500

            # Calculate total bet
            bet_amount = 0 if stake == 'practice' else int(stake)
            total_bet = bet_amount * len(cartella_ids)

            if deposit < total_bet and stake != 'practice':
                return jsonify({"status": "error", "message": "Insufficient balance"}), 403

            # Deduct balance
            if stake != 'practice':
                cursor.execute("UPDATE users SET deposit = deposit - ? WHERE id = ?", (total_bet, user_id))
                cursor.execute("""
                    UPDATE bingo_rounds 
                    SET total_bets = total_bets + ?
                    WHERE round_id = ?
                """, (total_bet, round_id))

            # Log game activity
            cursor.execute("""
                INSERT INTO game_activities (user_id, game_type, amount_lost, round_id)
                VALUES (?, 'bingo', ?, ?)
            """, (user_id, total_bet, round_id))

            conn.commit()

            return jsonify({
                "status": "success",
                "game_id": round_id,
                "new_balance": deposit - total_bet if stake != 'practice' else deposit
            }), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in start_game: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Get game state
@app.route('/<game_id>', methods=['GET'])
def get_game(game_id):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({"status": "error", "message": "Token required"}), 401

    try:
        with sqlite3.connect('transactions.db', timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id
                FROM users 
                WHERE bot_token = ? AND token_expiry > ?
            """, (token, int(time.time())))
            user = cursor.fetchone()
            if not user:
                return jsonify({"status": "error", "message": "Invalid or expired token"}), 401

            cursor.execute("""
                SELECT stake, timestamp, numbers, status
                FROM bingo_rounds
                WHERE round_id = ?
            """, (game_id,))
            round_data = cursor.fetchone()
            if not round_data:
                return jsonify({"status": "error", "message": "Game not found"}), 404

            stake, timestamp, numbers, status = round_data
            numbers = eval(numbers) if numbers else []
            timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f%z')

            return jsonify({
                "status": "success",
                "game_id": game_id,
                "stake": stake,
                "start_time": timestamp.isoformat(),
                "drawn_numbers": numbers,
                "game_status": status
            }), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in get_game: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Draw number
@app.route('/<game_id>/draw', methods=['POST'])
def draw_number(game_id):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not token:
        return jsonify({"status": "error", "message": "Token required"}), 401

    try:
        with sqlite3.connect('transactions.db', timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id
                FROM users 
                WHERE bot_token = ? AND token_expiry > ?
            """, (token, int(time.time())))
            user = cursor.fetchone()
            if not user:
                return jsonify({"status": "error", "message": "Invalid or expired token"}), 401

            cursor.execute("""
                SELECT numbers, status
                FROM bingo_rounds
                WHERE round_id = ?
            """, (game_id,))
            round_data = cursor.fetchone()
            if not round_data:
                return jsonify({"status": "error", "message": "Game not found"}), 404

            numbers, status = round_data
            numbers = eval(numbers) if numbers else []

            data = request.get_json()
            number = data.get('number')
            if not number or number in numbers:
                return jsonify({"status": "error", "message": "Invalid or duplicate number"}), 400

            numbers.append(number)
            cursor.execute("""
                UPDATE bingo_rounds
                SET numbers = ?
                WHERE round_id = ?
            """, (str(numbers), game_id))

            if len(numbers) >= NUMBERS_PER_ROUND:
                cursor.execute("""
                    UPDATE bingo_rounds
                    SET status = 'completed'
                    WHERE round_id = ?
                """, (game_id,))

            conn.commit()

            return jsonify({
                "status": "success",
                "drawn_numbers": numbers
            }), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in draw_number: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Place bet (when claiming Bingo)
@app.route('/place_bet', methods=['POST'])
def place_bet():
    data = request.get_json()
    token = data.get('token')
    cartella_ids = data.get('cartella_ids')
    bet_amount = data.get('bet_amount')
    pattern_type = data.get('pattern_type')
    round_id = data.get('round_id')

    if not all([token, cartella_ids, bet_amount, pattern_type, round_id]) or len(cartella_ids) > 2:
        logging.warning("Invalid request data received.")
        return jsonify({"status": "error", "message": "Invalid request data."}), 400

    try:
        with sqlite3.connect('transactions.db', timeout=10) as conn:
            cursor = conn.cursor()
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
            called_numbers = eval(round_data[0])
            total_bets, total_payouts = round_data[1], round_data[2]

            # Simple win check (server-side validation needed for patterns)
            required_patterns = 1 if pattern_type == 'single' else 2
            winnings = 0
            if len(called_numbers) >= 4:
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
                    f"{BaseUrl}/bot/notify",
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
        logging.error(f"Database error in place_bet: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
