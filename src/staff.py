import sqlite3
import requests
import logging
import secrets
from flask import Flask, request, jsonify
from flask_login import current_user, login_required

from src.payment import save_to_receipt_db, verify_receipt
from constant import RECEIPT_API_KEY, RECEIPT_API_URL

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@app.route('/staff/verify', methods=['POST'])
def staff_verify():
    data = request.get_json()
    transaction_id = data.get('transaction_id')
    action = data.get('action')
    telegram_id = data.get('telegram_id')

    if not all([transaction_id, action, telegram_id]):
        return jsonify({"status": "error", "message": "Transaction ID, action, and Telegram ID required."}), 400
    if action not in ['approve', 'reject']:
        return jsonify({"status": "error", "message": "Invalid action."}), 400

    try:
        with sqlite3.connect('transactions.db', timeout=10) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT amount, method, source, transaction_number, payer_name, payment_date
                FROM transactions WHERE id = ? AND verified = FALSE
            """, (transaction_id,))
            transaction = c.fetchone()
            if not transaction:
                return jsonify({"status": "error", "message": "Transaction not found or already verified."}), 404
            amount, method, source, transaction_number, payer_name, payment_date = transaction

            c.execute("SELECT id, deposit FROM users WHERE telegram_id = ?", (telegram_id,))
            user = c.fetchone()
            if not user:
                return jsonify({"status": "error", "message": "User not found."}), 404
            user_id, current_deposit = user

            if action == 'approve':
                if source != "manual":
                    # Verify with Receipt Project
                    receipt_data = verify_receipt(source, transaction_number)
                    if not receipt_data or "error" in receipt_data:
                        # Fallback to manual verification
                        manual_data = {
                            "source": "manual",
                            "receipt_id": transaction_number,
                            "amount": f"{amount} Birr",
                            "payer_name": payer_name or "Unknown",
                            "payer_phone_last4": "1234",
                            "game_user_id": str(user_id)
                        }
                        response = requests.post(
                            f"{RECEIPT_API_URL}/manual/flag",
                            json=manual_data,
                            headers={"X-API-Key": RECEIPT_API_KEY, "Content-Type": "application/json"},
                            timeout=5
                        )
                        if response.status_code != 200 or response.json().get("flag") != "green":
                            logging.error(f"Manual verification failed: {response.json().get('error')}")
                            return jsonify({"status": "error", "message": "Manual verification failed."}), 400
                        receipt_data = response.json()
                else:
                    receipt_data = {
                        "source": "manual",
                        "receipt_id": transaction_number,
                        "amount": str(amount),
                        "payer_name": payer_name,
                        "payment_date": payment_date,
                        "status": "Completed"
                    }

                c.execute("""
                    UPDATE transactions 
                    SET user_id = ?, telegram_id = ?, verified = TRUE, status = 'verified'
                    WHERE id = ?
                """, (user_id, telegram_id, transaction_id))
                c.execute("UPDATE users SET deposit = deposit + ? WHERE id = ?", (amount, user_id))
                conn.commit()
                logging.info(f"Staff approved transaction {transaction_id} for {telegram_id}")

                # Save to Receipt Project
                save_to_receipt_db(receipt_data)

                # Notify user
                notify_response = requests.post(
                    f"{BaseUrl}/notify",
                    json={
                        "telegram_id": telegram_id,
                        "message": f"Your deposit of {amount} ETB via {method} has been verified! 🎉 Your new balance is {current_deposit + amount} ETB."
                    },
                    timeout=5
                )
                if notify_response.status_code != 200:
                    logging.error(f"Failed to notify user {telegram_id}: {notify_response.json()}")

                return jsonify({"status": "success", "message": "Transaction approved."}), 200
            elif action == 'reject':
                c.execute("UPDATE transactions SET status = 'rejected' WHERE id = ?", (transaction_id,))
                conn.commit()
                logging.info(f"Staff rejected transaction {transaction_id}")

                # Notify user
                notify_response = requests.post(
                    f"{BaseUrl}/notify",
                    json={
                        "telegram_id": telegram_id,
                        "message": f"Your deposit transaction {transaction_number} was rejected. Please contact support."
                    },
                    timeout=5
                )
                if notify_response.status_code != 200:
                    logging.error(f"Failed to notify user {telegram_id}: {notify_response.json()}")

                return jsonify({"status": "success", "message": "Transaction rejected."}), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in staff_verify: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/staff/transactions', methods=['GET'])
@login_required
def staff_transactions():
    if not current_user.is_staff:
        return jsonify({"status": "error", "message": "Unauthorized."}), 403
    try:
        with sqlite3.connect('transactions.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, t.transaction_number, t.amount, t.method, t.source, t.payer_name, t.payment_date, t.sender, t.timestamp, t.raw_message, t.telegram_id, u.username
                FROM transactions t
                LEFT JOIN users u ON t.user_id = u.id
                WHERE t.verified = FALSE AND t.status = 'pending'
            """)
            transactions = [
                {
                    "id": t[0],
                    "transaction_number": t[1],
                    "amount": t[2],
                    "method": t[3],
                    "source": t[4],
                    "payer_name": t[5],
                    "payment_date": t[6],
                    "sender": t[7],
                    "timestamp": t[8],
                    "raw_message": t[9],
                    "telegram_id": t[10],
                    "username": t[11] or "Unknown"
                }
                for t in cursor.fetchall()
            ]
        return jsonify({"status": "success", "transactions": transactions}), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in staff_transactions: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
