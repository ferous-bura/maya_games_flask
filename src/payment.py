import re
import sqlite3
import time
import requests
import logging
import secrets
from flask import Blueprint, Flask, render_template, request, jsonify
from flask_login import LoginManager
from datetime import datetime, timezone

from utils import BaseUrl

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

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def verify_receipt(source, receipt_id):
    headers = {"X-API-Key": RECEIPT_API_KEY}
    if source == "telebirr":
        url = f"{RECEIPT_API_URL}/extract/telebirr?receipt_id={receipt_id}"
    elif source == "boa":
        url = f"{RECEIPT_API_URL}/extract/boa?trx={receipt_id}"
    elif source == "cbe":
        url = f"{RECEIPT_API_URL}/extract/cbe?id={receipt_id}"
    else:
        return None
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json()
        logging.error(f"Verification failed for {source} receipt {receipt_id}: {response.json().get('error')}")
        return None
    except requests.RequestException as e:
        logging.error(f"Error verifying {source} receipt {receipt_id}: {e}")
        return None

def save_to_receipt_db(data):
    headers = {"X-API-Key": RECEIPT_API_KEY, "Content-Type": "application/json"}
    if data.get("source") == "manual":
        url = f"{RECEIPT_API_URL}/manual/flag"
        payload = {
            "receipt_id": data["receipt_id"],
            "amount": f"{data['amount']} Birr",
            "payer_name": data["payer_name"],
            "payer_phone_last4": data.get("payer_phone_last4", "1234"),
            "game_user_id": data.get("game_user_id")
        }
    else:
        url = f"{RECEIPT_API_URL}/extract/{data['source']}"
        payload = data
    try:
        response = requests.get(url, headers=headers, json=payload, timeout=5)
        if response.status_code == 200:
            logging.info(f"Saved to Receipt Project DB: {data['receipt_id']}")
            return True
        logging.error(f"Failed to save to Receipt Project DB: {response.json().get('error')}")
        return False
    except requests.RequestException as e:
        logging.error(f"Error saving to Receipt Project DB: {e}")
        return False

def parse_telebirr_to_telebirr_sms(raw_message):
    """Parse Telebirr to Telebirr transfer SMS."""
    match = re.search(
        r'You have transferred ETB ([\d,]+\.\d{2}) to [\w\s]+(?:\s*\(\d+\*\*\*\*\d+\))? on ([\d/ :]+)\. Your transaction number is ([A-Z0-9]+)',
        raw_message, re.IGNORECASE
    )
    if match:
        amount = float(match.group(1).replace(",", ""))
        payment_date = match.group(2)
        transaction_number = match.group(3)
        payer_name_match = re.search(r'Dear ([\w\s]+),', raw_message, re.IGNORECASE)
        payer_name = payer_name_match.group(1).strip() if payer_name_match else None
        return {
            "amount": amount,
            "transaction_number": transaction_number,
            "payer_name": payer_name,
            "payment_date": payment_date,
            "method": "telebirr",
            "source": "telebirr",
            "sender": payer_name
        }
    return None

def parse_boa_to_telebirr_sms(raw_message):
    """Parse BoA to Telebirr transfer SMS."""
    match = re.search(
        r'credited with ETB ([\d,]+\.\d{2}) by A/R TELE BIRR.*?trx=([A-Z0-9]+)',
        raw_message, re.IGNORECASE
    )
    if match:
        amount = float(match.group(1).replace(",", ""))
        transaction_number = match.group(2)
        payer_name_match = re.search(r'Dear ([\w\s]+),', raw_message, re.IGNORECASE)
        payer_name = payer_name_match.group(1).strip() if payer_name_match else None
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        return {
            "amount": amount,
            "transaction_number": transaction_number,
            "payer_name": payer_name,
            "payment_date": timestamp,  # BoA SMS lacks date
            "method": "bank_abyssinia",
            "source": "boa",
            "sender": payer_name
        }
    return None

def parse_telebirr_to_boa_sms(raw_message):
    """Parse Telebirr to BoA transfer SMS."""
    match = re.search(
        r'You have transferred ETB ([\d,]+\.\d{2}) .*?to Bank of Abyssinia account number \d+ on ([\d/ :]+)\. Your telebirr transaction number is ([A-Z0-9]+)',
        raw_message, re.IGNORECASE
    )
    if match:
        amount = float(match.group(1).replace(",", ""))
        payment_date = match.group(2)
        transaction_number = match.group(3)
        payer_name_match = re.search(r'Dear ([\w\s]+),', raw_message, re.IGNORECASE)
        payer_name = payer_name_match.group(1).strip() if payer_name_match else None
        return {
            "amount": amount,
            "transaction_number": transaction_number,
            "payer_name": payer_name,
            "payment_date": payment_date,
            "method": "telebirr",
            "source": "telebirr",  # Source is Telebirr as the transfer originates there
            "sender": payer_name
        }
    return None

def parse_cbe_to_telebirr_sms(raw_message):
    """Parse CBE to Telebirr transfer SMS."""
    match = re.search(
        r'Credited with ETB ([\d,]+\.\d{2})\..*?id=([A-Z0-9]+)',
        raw_message, re.IGNORECASE
    )
    if match:
        amount = float(match.group(1).replace(",", ""))
        transaction_number = match.group(2)
        payer_name_match = re.search(r'Dear ([\w\s]+),', raw_message, re.IGNORECASE)
        payer_name = payer_name_match.group(1).strip() if payer_name_match else None
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        return {
            "amount": amount,
            "transaction_number": transaction_number,
            "payer_name": payer_name,
            "payment_date": timestamp,  # CBE SMS lacks date
            "method": "cbe",
            "source": "cbe",
            "sender": payer_name
        }
    return None

def parse_transfer_sms(raw_message):
    """Parse transfer SMS and return transaction details."""
    parsers = [
        parse_telebirr_to_telebirr_sms,
        parse_boa_to_telebirr_sms,
        parse_telebirr_to_boa_sms,
        parse_cbe_to_telebirr_sms
    ]
    for parser in parsers:
        result = parser(raw_message)
        if result:
            logging.info(f"Parsed SMS with {parser.__name__}: {result}")
            return result
    logging.error(f"Failed to parse transfer SMS: {raw_message}")
    return None

@payment_blueprint.route('/', methods=['POST'])
def payment():
    data = request.get_json()
    raw_message = data.get('raw_message')
    telegram_id = data.get('telegram_id')
    if not raw_message or not telegram_id:
        logging.error("Missing raw_message or telegram_id in payment request")
        return jsonify({"status": "error", "message": "Raw message and Telegram ID required."}), 400

    try:
        # Parse transfer SMS
        transaction_data = parse_transfer_sms(raw_message)
        if not transaction_data:
            return jsonify({"status": "error", "message": "Invalid SMS format."}), 400

        amount = transaction_data["amount"]
        transaction_number = transaction_data["transaction_number"]
        payer_name = transaction_data["payer_name"]
        payment_date = transaction_data["payment_date"]
        method = transaction_data["method"]
        source = transaction_data["source"]
        sender = transaction_data["sender"]
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        with sqlite3.connect('transactions.db', timeout=10) as conn:
            c = conn.cursor()
            # Check for duplicate transaction
            c.execute("SELECT id FROM transactions WHERE transaction_number = ?", (transaction_number,))
            if c.fetchone():
                logging.info(f"Duplicate transaction: {transaction_number}")
                return jsonify({"status": "success", "message": "Transaction already processed."}), 200

            # Get user_id from telegram_id
            c.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user = c.fetchone()
            if not user:
                logging.error(f"User not found for telegram_id: {telegram_id}")
                return jsonify({"status": "error", "message": "User not found."}), 404
            user_id = user[0]

            # Verify with Receipt Project
            receipt_data = verify_receipt(source, transaction_number)
            logging.info(f"Receipt verification response: {receipt_data}")
            if receipt_data and "error" not in receipt_data:
                status = "verified"
                verified = True
                # Update fields from Receipt Project if available
                amount = float(re.sub(r'[^\d.]', '', receipt_data.get("amount", str(amount))))
                payer_name = receipt_data.get("payer_name", payer_name)
                payment_date = receipt_data.get("payment_date", payment_date) or timestamp
            else:
                status = "pending"
                verified = False

            # Insert transaction
            c.execute("""
                INSERT INTO transactions (
                    user_id, telegram_id, transaction_number, amount, method, source, 
                    payer_name, payment_date, sender, raw_message, timestamp, verified, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, telegram_id, transaction_number, amount, method, source,
                payer_name, payment_date, sender, raw_message, timestamp, verified, status
            ))
            conn.commit()
            logging.info(f"Inserted transaction: {transaction_number}, status={status}")

            # Save to Receipt Project if verified
            if verified:
                save_to_receipt_db(receipt_data)
                # Update user deposit
                c.execute("UPDATE users SET deposit = deposit + ? WHERE id = ?", (amount, user_id))
                conn.commit()
                # Notify user
                notify_response = requests.post(
                    f"{BaseUrl}/notify",
                    json={
                        "telegram_id": telegram_id,
                        "message": f"Your deposit of {amount} ETB via {method} has been verified! 🎉"
                    },
                    timeout=5
                )
                if notify_response.status_code != 200:
                    logging.error(f"Failed to notify user {telegram_id}: {notify_response.json()}")

        return jsonify({"status": "success", "message": f"Transaction {status}."}), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in payment: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@payment_blueprint.route('/pending_deposits', methods=['POST'])
def pending_deposits():
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    if not telegram_id:
        return jsonify({"status": "error", "message": "Telegram ID required."}), 400

    try:
        with sqlite3.connect('transactions.db') as conn:
            c = conn.cursor()
            c.execute("""
                SELECT transaction_number, amount, method, source, payer_name, payment_date, timestamp 
                FROM transactions 
                WHERE telegram_id = ? AND verified = FALSE AND status = 'pending'
            """, (telegram_id,))
            pending = [
                {
                    "transaction_number": t[0],
                    "amount": t[1],
                    "method": t[2],
                    "source": t[3],
                    "payer_name": t[4],
                    "payment_date": t[5],
                    "timestamp": t[6]
                }
                for t in c.fetchall()
            ]
        return jsonify({"status": "success", "pending_deposits": pending}), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in pending_deposits: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@payment_blueprint.route('/trx', methods=['GET'])
def transactions():
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
                WHERE user_id = ?
                ORDER BY timestamp DESC 
                LIMIT 20
            """, (user_id,))
            transactions = [
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
        return jsonify({"status": "success", "transactions": transactions}), 200
    except sqlite3.Error as e:
        logging.error(f"Database error in transactions: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@payment_blueprint.route('/transactions', methods=['GET'])
def trx():
    return render_template('transactions.html', transactions=transactions)
