import threading
import asyncio
from flask import Flask, request, jsonify
import sqlite3
import requests
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, Application
from bot_handler import main

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Replace with your bot token
TELEGRAM_BOT_TOKEN = "7637824158:AAFwZzrqiipVkKcl7V3_OFv46VCyL79v0"

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

# Expose the checker method to bot_handler.py
app.config['checker'] = checker

# Initialize Telegram bot
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("webapps", open_web_apps))

def run_flask():
    logging.debug("Starting Flask server...")
    app.run(debug=True, host="0.0.0.0", use_reloader=False)  # Disable reloader to avoid thread conflicts

def run_telegram_bot():
    async def start_bot():
        await application.initialize()
        await application.start()
        print("Telegram bot is running...")
        try:
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            await application.stop()

    asyncio.run(main())
    # asyncio.run(start_bot())

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    telegram_thread = threading.Thread(target=run_telegram_bot)

    flask_thread.start()
    telegram_thread.start()

    flask_thread.join()
    telegram_thread.join()

