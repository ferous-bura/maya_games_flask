import sqlite3
import logging
import secrets
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from colorlog import ColoredFormatter
from constant import ODD_PRICE, BaseUrl

# Configure logging with colors
formatter = ColoredFormatter(
    "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
    datefmt='%Y-%m-%d %H:%M:%S',
    log_colors={
        'DEBUG': 'white',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    },
    secondary_log_colors={
        'message': {
            'scheduler': 'cyan',
            'round': 'blue',
            'generate numbers': 'magenta',
        }
    }
)

handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.getLogger().handlers = [handler]
logging.getLogger().setLevel(logging.INFO)

keno_blueprint = Blueprint('keno', __name__)

scheduler = BackgroundScheduler()
scheduler.start()

# Game constants
TOTAL_NUMBERS = 80
DRAW_NUMBERS = 20
ROUND_DURATION = 60  # seconds
RESULT_GENERATION_TIME = 31  # seconds
INTERACTION_CUTOFF = 6  # seconds before selection ends
KENO_RTP = 0.92

class KenoGame:
    def __init__(self, db_path='transactions.db'):
        self.db_path = db_path
        self.current_round = None
        self.schedule_round()

    def create_new_round(self):
        """Create a new Keno round."""
        now = datetime.now(timezone.utc)
        round_id = str(uuid.uuid4())
        new_round = {
            'round_id': round_id,
            'timestamp': now,
            'numbers': [],
            'status': 'SELECT',
            'results': []
        }
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO keno_rounds (round_id, timestamp, numbers, total_bets, total_payouts)
                VALUES (?, ?, '[]', 0.0, 0.0)
            """, (round_id, now))
            conn.commit()
        logging.info(f"Created new round: {round_id}", extra={'secondary_log_color': 'round'})
        return new_round

    def generate_numbers(self, round_id):
        """Generate numbers for a round, controlling RTP."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT numbers, amount_lost, odd_type 
                    FROM game_activities 
                    WHERE game_type = 'keno' AND round_id = ? AND is_paid = TRUE
                """, (round_id,))
                bets = cursor.fetchall()

                total_bets = sum(bet['amount_lost'] for bet in bets)
                target_payout = total_bets * KENO_RTP

                if not bets or total_bets == 0:
                    logging.info(f"No bets for round {round_id}. Using random numbers.", extra={'secondary_log_color': 'generate numbers'})
                    return self._random_numbers()

                best_draw = None
                best_payout_diff = float('inf')
                all_numbers = list(range(1, 81))

                for _ in range(100):
                    random.seed(str(round_id) + str(_))
                    candidate = random.sample(all_numbers, 20)
                    total_payout = 0
                    for bet in bets:
                        bet_numbers = eval(bet['numbers']) if bet['numbers'] else []
                        hits = len(set(bet_numbers) & set(candidate))
                        odds = self.calculate_odds(hits, len(bet_numbers), bet['odd_type'] or 'kiron')
                        total_payout += odds * bet['amount_lost'] * KENO_RTP

                    payout_diff = abs(total_payout - target_payout)
                    if payout_diff < best_payout_diff:
                        best_payout_diff = payout_diff
                        best_draw = candidate

                    if payout_diff < total_bets * 0.01:
                        break

                if best_draw:
                    logging.info(f"Round {round_id}: Selected draw {best_draw}", extra={'secondary_log_color': 'generate numbers'})
                    return best_draw
                logging.warning(f"Round {round_id}: No optimal draw found. Using random numbers.", extra={'secondary_log_color': 'generate numbers'})
                return self._random_numbers()

        except sqlite3.Error as e:
            logging.error(f"Database error in generate_numbers: {e}", extra={'secondary_log_color': 'generate numbers'})
            return self._random_numbers()

    def _random_numbers(self):
        """Generate 20 unique random numbers."""
        numbers = []
        while len(numbers) < 20:
            num = secrets.randbelow(80) + 1
            if num not in numbers:
                numbers.append(num)
        return sorted(numbers)

    def calculate_odds(self, hits, total_balls, odd_type):
        """Calculate Keno odds based on hits and odd type."""
        odds = 0
        if odd_type in ODD_PRICE and total_balls in ODD_PRICE[odd_type]:
            for hit_balls, odds_value in ODD_PRICE[odd_type][total_balls]:
                if hit_balls == hits:
                    odds = odds_value
                    break
        return odds

    def get_odds_breakdown(self, total_balls, odd_type):
        """Return the odds breakdown for a given number of selected balls and odd type."""
        if odd_type in ODD_PRICE and total_balls in ODD_PRICE[odd_type]:
            return ODD_PRICE[odd_type][total_balls]
        return []

    def get_current_round(self, user_balance):
        """Get or create the current round."""
        now = datetime.now(timezone.utc)
        if not self.current_round or (now - self.current_round['timestamp']).total_seconds() >= ROUND_DURATION:
            self.current_round = self.create_new_round()

        elapsed = (now - self.current_round['timestamp']).total_seconds()
        time_left = max(0, ROUND_DURATION - elapsed)

        if elapsed >= RESULT_GENERATION_TIME and not self.current_round['numbers']:
            self.current_round['numbers'] = self.generate_numbers(self.current_round['round_id'])
            self.current_round['status'] = 'SHOWING_RESULT'
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE keno_rounds 
                    SET numbers = ?
                    WHERE round_id = ?
                """, (str(self.current_round['numbers']), self.current_round['round_id']))
                conn.commit()
                logging.info(f"Generated numbers for round {self.current_round['round_id']}: {self.current_round['numbers']}")

        round_status = 'SELECT' if elapsed < RESULT_GENERATION_TIME else 'SHOWING_RESULT'

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT numbers, amount_won
                FROM game_activities
                WHERE round_id = ? AND game_type = 'keno' AND is_paid = TRUE
            """, (self.current_round['round_id'],))
            results = [{"numbers": eval(row['numbers']), "winnings": row['amount_won']} for row in cursor.fetchall()]

        return {
            'status': 'success',
            'round_id': self.current_round['round_id'],
            'round_status': round_status,
            'time_left': time_left,
            'numbers': self.current_round['numbers'],
            'results': results,
            'balance': float(user_balance)
        }

    def schedule_round(self):
        """Schedule a new round every 60 seconds."""
        def job():
            self.current_round = self.create_new_round()
            scheduler.add_job(
                lambda: self.generate_numbers(self.current_round['round_id']),
                'date',
                run_date=self.current_round['timestamp'] + timedelta(seconds=RESULT_GENERATION_TIME),
                id=f"generate_numbers_{self.current_round['round_id']}",
                replace_existing=True
            )

        scheduler.add_job(
            job,
            'interval',
            seconds=ROUND_DURATION,
            id='keno_round',
            next_run_time=datetime.now(timezone.utc),
            replace_existing=True
        )
        logging.info("Scheduler initialized for Keno rounds.", extra={'secondary_log_color': 'scheduler'})

# Initialize game
keno_game = KenoGame()

@keno_blueprint.route('/current_round', methods=['GET'])
def keno_current_round():
    """Fetch the current Keno round details."""
    token = request.args.get('token')
    if not token:
        return jsonify({"status": "error", "message": "Token required."}), 400

    try:
        with sqlite3.connect('transactions.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT deposit FROM users WHERE bot_token = ? AND token_expiry > ?", 
                         (token, int(time.time())))
            user = cursor.fetchone()
            if not user:
                return jsonify({"status": "error", "message": "Invalid or expired token."}), 401
            balance = user['deposit']
            return jsonify(keno_game.get_current_round(balance)), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in keno_current_round: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@keno_blueprint.route('/place_bet', methods=['POST'])
def keno_place_bet():
    """Place a single Keno bet."""
    data = request.get_json()
    token = data.get('token')
    ticket = data.get('ticket')
    round_id = data.get('round_id')

    if not all([token, ticket, round_id]) or not isinstance(ticket, dict):
        logging.warning("Invalid request data received.")
        return jsonify({"status": "error", "message": "Invalid request data."}), 400

    if 'numbers' not in ticket or 'stake' not in ticket or not isinstance(ticket['numbers'], list):
        logging.warning("Invalid ticket data.")
        return jsonify({"status": "error", "message": "Invalid ticket data."}), 400

    try:
        with sqlite3.connect('transactions.db', timeout=10) as conn:
            conn.row_factory = sqlite3.Row
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

            cursor.execute("SELECT timestamp FROM keno_rounds WHERE round_id = ?", (round_id,))
            round_data = cursor.fetchone()
            if not round_data:
                logging.warning("Round not found.")
                return jsonify({"status": "error", "message": "Round not found."}), 404
            timestamp = datetime.strptime(str(round_data['timestamp']), '%Y-%m-%d %H:%M:%S.%f%z')
            seconds_since_start = (datetime.now(timezone.utc) - timestamp).total_seconds()
            time_left = ROUND_DURATION - seconds_since_start
            if time_left < INTERACTION_CUTOFF:
                logging.warning("Betting closed for this round.")
                return jsonify({"status": "error", "message": "Betting closed for this round."}), 403

            total_bet = ticket['stake']
            if deposit < total_bet:
                logging.warning("Insufficient balance for user.")
                return jsonify({"status": "error", "message": "Insufficient balance."}), 403

            cursor.execute("SELECT numbers FROM keno_rounds WHERE round_id = ?", (round_id,))
            round_data = cursor.fetchone()
            drawn_numbers = eval(round_data['numbers']) if round_data['numbers'] else []
            hits = len(set(ticket['numbers']) & set(drawn_numbers))
            odds = keno_game.calculate_odds(hits, len(ticket['numbers']), ticket.get('odd_type', 'kiron'))
            winnings = odds * ticket['stake'] * KENO_RTP
            odds_breakdown = keno_game.get_odds_breakdown(len(ticket['numbers']), ticket.get('odd_type', 'kiron'))
            potential_win = ticket['stake'] * odds_breakdown[-1][1] if odds_breakdown else 0

            cursor.execute("UPDATE users SET deposit = deposit - ? + ? WHERE id = ?", (total_bet, winnings, user_id))
            cursor.execute("""
                UPDATE keno_rounds 
                SET total_bets = total_bets + ?, total_payouts = total_payouts + ?
                WHERE round_id = ?
            """, (total_bet, winnings, round_id))
            cursor.execute("""
                INSERT INTO game_activities (user_id, game_type, amount_won, amount_lost, is_paid, round_id, numbers, odd_type)
                VALUES (?, 'keno', ?, ?, TRUE, ?, ?, ?)
            """, (user_id, winnings, total_bet, round_id, str(ticket['numbers']), ticket.get('odd_type', 'kiron')))
            cursor.execute("SELECT last_insert_rowid()")
            ticket_id = cursor.fetchone()[0]
            conn.commit()

            logging.info(f"Bet placed successfully for user_id={user_id}, ticket_id={ticket_id}, winnings={winnings}")

            if winnings > 0:
                requests.post(
                    f"{BaseUrl}/notify",
                    json={
                        "telegram_id": telegram_id,
                        "message": f"🎉 Keno Round {round_id}: You won {winnings:.2f} ETB! New balance: {deposit - total_bet + winnings:.2f} ETB."
                    },
                    timeout=5
                )

            return jsonify({
                "status": "success",
                "ticket_id": ticket_id,
                "winnings": winnings,
                "new_balance": deposit - total_bet + winnings,
                "odds_breakdown": odds_breakdown,
                "potential_win": potential_win
            }), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in keno_place_bet: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@keno_blueprint.route('/ticket_history', methods=['GET'])
def ticket_history():
    """Fetch the ticket history for the user."""
    token = request.args.get('token')
    if not token:
        return jsonify({"status": "error", "message": "Token required."}), 400

    try:
        with sqlite3.connect('transactions.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM users WHERE bot_token = ? AND token_expiry > ?
            """, (token, int(time.time())))
            user = cursor.fetchone()
            if not user:
                return jsonify({"status": "error", "message": "Invalid or expired token."}), 401

            user_id = user[0]
            cursor.execute("""
                SELECT round_id, numbers, amount_won, amount_lost, timestamp
                FROM game_activities
                WHERE user_id = ? AND game_type = 'keno'
                ORDER BY timestamp DESC
            """, (user_id,))
            tickets = [
                {
                    "round_id": row[0],
                    "numbers": eval(row[1]) if row[1] else [],
                    "bet_amount": row[3] if row[3] else 0,
                    "winnings": row[2] if row[2] else 0,
                    "timestamp": row[4]
                }
                for row in cursor.fetchall()
            ]

        return jsonify({"status": "success", "tickets": tickets}), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in ticket_history: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@keno_blueprint.route('/cancel_bet', methods=['POST'])
def keno_cancel_bet():
    """Cancel all bets for a user in a specific round."""
    data = request.get_json()
    token = data.get('token')
    round_id = data.get('round_id')

    if not all([token, round_id]):
        logging.warning("Invalid request data received.")
        return jsonify({"status": "error", "message": "Invalid request data."}), 400

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
                logging.warning("Invalid or expired token.")
                return jsonify({"status": "error", "message": "Invalid or expired token."}), 401
            user_id, deposit = user

            cursor.execute("SELECT timestamp FROM keno_rounds WHERE round_id = ?", (round_id,))
            round_data = cursor.fetchone()
            if not round_data:
                logging.warning("Round not found.")
                return jsonify({"status": "error", "message": "Round not found."}), 404
            timestamp = datetime.strptime(str(round_data[0]), '%Y-%m-%d %H:%M:%S.%f%z')
            seconds_since_start = (datetime.now(timezone.utc) - timestamp).total_seconds()
            time_left = ROUND_DURATION - seconds_since_start
            if time_left < INTERACTION_CUTOFF:
                logging.warning("Bet cancellation closed for this round.")
                return jsonify({"status": "error", "message": "Bet cancellation closed for this round."}), 403

            cursor.execute("""
                SELECT amount_lost
                FROM game_activities
                WHERE user_id = ? AND round_id = ? AND game_type = 'keno' AND is_paid = TRUE
            """, (user_id, round_id))
            bets = cursor.fetchall()
            if not bets:
                logging.warning("No bets found for cancellation.")
                return jsonify({"status": "error", "message": "No bets found for this round."}), 404

            total_refunded = sum(bet[0] for bet in bets)
            cursor.execute("UPDATE users SET deposit = deposit + ? WHERE id = ?", (total_refunded, user_id))
            cursor.execute("""
                DELETE FROM game_activities
                WHERE user_id = ? AND round_id = ? AND game_type = 'keno'
            """, (user_id, round_id))
            cursor.execute("""
                UPDATE keno_rounds
                SET total_bets = total_bets - ?
                WHERE round_id = ?
            """, (total_refunded, round_id))
            conn.commit()

            logging.info(f"Bets canceled for user_id={user_id}, round_id={round_id}, refunded={total_refunded}")

            return jsonify({
                "status": "success",
                "new_balance": deposit + total_refunded
            }), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in keno_cancel_bet: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@keno_blueprint.route('/cancel_ticket', methods=['POST'])
def keno_cancel_ticket():
    """Cancel a single ticket for a user."""
    data = request.get_json()
    token = data.get('token')
    ticket_id = data.get('ticket_id')

    if not all([token, ticket_id]):
        logging.warning("Invalid request data received.")
        return jsonify({"status": "error", "message": "Invalid request data."}), 400

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
                logging.warning("Invalid or expired token.")
                return jsonify({"status": "error", "message": "Invalid or expired token."}), 401
            user_id, deposit = user

            cursor.execute("""
                SELECT amount_lost, round_id
                FROM game_activities
                WHERE id = ? AND user_id = ? AND game_type = 'keno' AND is_paid = TRUE
            """, (ticket_id, user_id))
            bet = cursor.fetchone()
            if not bet:
                logging.warning("Ticket not found for cancellation.")
                return jsonify({"status": "error", "message": "Ticket not found."}), 404
            amount_lost, round_id = bet

            cursor.execute("SELECT timestamp FROM keno_rounds WHERE round_id = ?", (round_id,))
            round_data = cursor.fetchone()
            if not round_data:
                logging.warning("Round not found.")
                return jsonify({"status": "error", "message": "Round not found."}), 404
            timestamp = datetime.strptime(str(round_data[0]), '%Y-%m-%d %H:%M:%S.%f%z')
            seconds_since_start = (datetime.now(timezone.utc) - timestamp).total_seconds()
            time_left = ROUND_DURATION - seconds_since_start
            if time_left < INTERACTION_CUTOFF:
                logging.warning("Ticket cancellation closed for this round.")
                return jsonify({"status": "error", "message": "Ticket cancellation closed for this round."}), 403

            cursor.execute("UPDATE users SET deposit = deposit + ? WHERE id = ?", (amount_lost, user_id))
            cursor.execute("""
                DELETE FROM game_activities
                WHERE id = ? AND user_id = ?
            """, (ticket_id, user_id))
            cursor.execute("""
                UPDATE keno_rounds
                SET total_bets = total_bets - ?
                WHERE round_id = ?
            """, (amount_lost, round_id))
            conn.commit()

            logging.info(f"Ticket canceled for user_id={user_id}, ticket_id={ticket_id}, refunded={amount_lost}")

            return jsonify({
                "status": "success",
                "new_balance": deposit + amount_lost
            }), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in keno_cancel_ticket: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500