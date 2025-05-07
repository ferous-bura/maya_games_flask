import sqlite3
import random
from flask import jsonify, render_template, request
from flask_login import current_user, login_required
import logging

import app as app


@app.app.route('/play3/<game_type>', methods=['GET', 'POST'])
@login_required
def play_game(game_type):
    if game_type not in ['keno', 'bingo', 'spin', 'ludo']:
        return jsonify({"status": "error", "message": "Invalid game type."}), 400

    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT deposit FROM users WHERE id = ?", (current_user.id,))
        deposit = cursor.fetchone()[0]

    if request.method == 'POST':
        bet_amount = float(request.form.get('bet_amount', 0))
        if bet_amount <= 0 or bet_amount > deposit:
            logging.error(f"Invalid bet amount: {bet_amount}, Deposit: {deposit}")
            return jsonify({"status": "error", "message": "Invalid or insufficient bet amount."}), 400

        amount_won = 0
        amount_lost = bet_amount
        is_paid = False

        # Game-specific logic
        if game_type == 'keno':
            # Keno: Pick 10 numbers, match against 20 drawn numbers
            player_numbers = request.form.getlist('numbers', type=int)
            if len(player_numbers) != 10:
                return jsonify({"status": "error", "message": "Select exactly 10 numbers."}), 400
            drawn_numbers = random.sample(range(1, 81), 20)
            matches = len(set(player_numbers) & set(drawn_numbers))
            if matches >= 5:  # Simplified win condition
                amount_won = bet_amount * (matches - 4)  # Scale winnings
                amount_lost = 0
                is_paid = True
        elif game_type == 'bingo':
            # Bingo: Simple win/lose for demo
            if random.random() > 0.7:  # 30% chance to win
                amount_won = bet_amount * 3
                amount_lost = 0
                is_paid = True
        elif game_type == 'spin':
            # Spin: Wheel with multipliers
            outcomes = [0, 0.5, 1, 2, 5]
            multiplier = random.choice(outcomes)
            if multiplier > 0:
                amount_won = bet_amount * multiplier
                amount_lost = 0
                is_paid = True
        elif game_type == 'ludo':
            # Ludo: Simplified match outcome
            if random.random() > 0.6:  # 40% chance to win
                amount_won = bet_amount * 2
                amount_lost = 0
                is_paid = True

        # Update database
        with sqlite3.connect("transactions.db") as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET deposit = deposit + ? - ? WHERE id = ?", 
                         (amount_won, amount_lost, current_user.id))
            cursor.execute("""
                INSERT INTO game_activities (user_id, game_type, amount_won, amount_lost, is_paid)
                VALUES (?, ?, ?, ?, ?)
            """, (current_user.id, game_type, amount_won, amount_lost, is_paid))
            conn.commit()

        logging.info(f"Played {game_type} by user {current_user.id}: Won {amount_won}, Lost {amount_lost}")
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

    return render_template(f'templates/{game_type}.html', deposit=deposit)