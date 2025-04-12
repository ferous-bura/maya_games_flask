import threading
from flask import Flask, request, jsonify
import sqlite3
import requests
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Replace with your bot token
TELEGRAM_BOT_TOKEN = '8177364831:AAF8xaUob11YhX5kUr-1AXS11KY9o5QJERI'

# Dummy map (you can replace this with database mapping)
PHONE_TO_TELEGRAM = {
    "+251911223344": 7831842753,  # Replace with real Telegram user IDs
    "+251922334455": 5587470125
}
# Create the database (if not exists)
def init_db():
    logging.debug("Initializing the database...")
    with sqlite3.connect("transactions.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_code TEXT,
                amount TEXT,
                phone TEXT,
                sender TEXT,
                raw_message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    logging.debug("Database initialized.")
init_db()

@app.route('/')
def home():
    return "Welcome to the Flask App!"

@app.route('/ping')
def ping():
    return "Ping successful!"

@app.route('/payment', methods=['POST'])
def payment():
    logging.debug("Received a payment request.")
    data = request.get_json()
    logging.debug(f"Request data: {data}")

    transaction_code = data.get('transaction_code')
    amount = data.get('amount')
    phone = data.get('phone')
    sender = data.get('sender')
    raw_message = data.get('raw_message')

    # Store in SQLite
    logging.debug("Storing transaction in the database...")
    with sqlite3.connect("transactions.db") as conn:
        conn.execute("""
            INSERT INTO transactions (transaction_code, amount, phone, sender, raw_message)
            VALUES (?, ?, ?, ?, ?)
        """, (transaction_code, amount, phone, sender, raw_message))
    logging.debug("Transaction stored successfully.")

    # Send Telegram message if phone is linked
    if phone in PHONE_TO_TELEGRAM:
        chat_id = PHONE_TO_TELEGRAM[phone]
        msg = f"✅ Payment received!\nAmount: {amount} ETB\nTransaction: {transaction_code}"
        logging.debug(f"Sending Telegram message to chat_id {chat_id}: {msg}")
        send_telegram_message(chat_id, msg)

    logging.debug(f"Payment processing completed for phone: {phone}")
    return jsonify({"status": "success", "message": f"Stored and notified for {phone}"}), 200

@app.route('/process_payment', methods=['POST'])
def process_payment():
    data = request.get_json()
    transaction_number = data.get('transaction_number')
    amount = data.get('amount')
    sender = data.get('sender')
    raw_message = data.get('raw_message')

    # Save the payment to the database
    with sqlite3.connect("transactions.db") as conn:
        conn.execute(
            """
            INSERT INTO transactions (transaction_code, amount, sender, raw_message, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (transaction_number, amount, sender, raw_message)
        )

    logging.info(f"Processed payment: {transaction_number}, Amount: {amount}, Sender: {sender}")
    return jsonify({"status": "success", "message": "Payment processed successfully."}), 200

@app.route('/check_transaction', methods=['POST'])
def check_transaction():
    data = request.get_json()
    transaction_number = data.get('transaction_number')
    logging.debug(f"Checking transaction: {transaction_number}")
    # Validate input
    if not transaction_number:
        logging.error("Transaction number is missing.")
        return jsonify({"status": "error", "message": "Transaction number is required."}), 400
    # Check if transaction number is valid
    if not isinstance(transaction_number, str):
        logging.error("Invalid transaction number format.")
        return jsonify({"status": "error", "message": "Invalid transaction number format."}), 400
    # Check if transaction number is empty
    if transaction_number.strip() == "":
        logging.error("Transaction number is empty.")
        return jsonify({"status": "error", "message": "Transaction number cannot be empty."}), 400
    # Check if transaction number is too long
    if len(transaction_number) > 50:
        logging.error("Transaction number is too long.")
        return jsonify({"status": "error", "message": "Transaction number is too long."}), 400
    # Check if transaction number is too short
    if len(transaction_number) < 5:
        logging.error("Transaction number is too short.")
        return jsonify({"status": "error", "message": "Transaction number is too short."}), 400
    # Check if transaction number contains invalid characters
    if not transaction_number.isalnum():
        logging.error("Transaction number contains invalid characters.")
        return jsonify({"status": "error", "message": "Transaction number contains invalid characters."}), 400
    # Check if transaction number is a valid format (e.g., starts with 'TXN')
    # if not transaction_number.startswith("TXN"):
    #     logging.error("Transaction number does not start with 'TXN'.")
    #     return jsonify({"status": "error", "message": "Transaction number must start with 'TXN'."}), 400

    # Query the database for the transaction
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM transactions WHERE transaction_code = ?
            """,
            (transaction_number,)
        )
        result = cursor.fetchone()
    amount = result[2] if result else None #TODO: Check if result is is transfered amount
    totalDeposit = result[3] if result else None #TODO: Check if result is total deposit
    if result:
        logging.info(f"Transaction found: {result}")
        return jsonify({"status": "success", "message": f"{amount} is deposited, Total Deposit is {totalDeposit}"})#f"Transaction details: {result}"}), 200
    else:
        logging.warning(f"Transaction not found: {transaction_number}")
        return jsonify({"status": "error", "message": "Transaction not found."}), 404

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    logging.debug(f"Sending POST request to Telegram API: {url} with payload: {payload}")
    r = requests.post(url, json=payload)
    logging.debug(f"Telegram response: {r.status_code}, {r.text}")

# Add a method to send a message with web app links
def open_web_apps(update, context):
    keyboard = [
        [InlineKeyboardButton("Web App 1", url="https://example.com/webapp1")],
        [InlineKeyboardButton("Web App 2", url="https://example.com/webapp2")],
        [InlineKeyboardButton("Web App 3", url="https://example.com/webapp3")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Choose a web app to open:", reply_markup=reply_markup)

# Checker method to compare messages
async def checker(transaction_number, amount, sender, raw_message, timestamp):
    logging.debug("Running checker method...")

    # Save the incoming message to the database
    with sqlite3.connect("transactions.db") as conn:
        conn.execute(
            """
            INSERT INTO transactions (transaction_code, amount, sender, raw_message, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (transaction_number, amount, sender, raw_message, timestamp)
        )

    # Compare with existing messages in the database
    with sqlite3.connect("transactions.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM transactions WHERE transaction_code = ? AND amount = ?
            """,
            (transaction_number, amount)
        )
        result = cursor.fetchone()

    if result:
        logging.info(f"Match found for transaction {transaction_number}.")
    else:
        logging.warning(f"No match found for transaction {transaction_number}.")

def run_flask():
    logging.debug("Starting Flask server...")
    app.run(debug=True, host="0.0.0.0", use_reloader=False)  # Disable reloader to avoid thread conflicts


if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    flask_thread.join()
