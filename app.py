import threading
from flask import Flask, request, jsonify
import sqlite3
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

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

    logging.debug(f"Payment processing completed for phone: {phone}")
    return jsonify({"status": "success", "message": f"Stored transaction for {phone}"}), 200

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

    if result:
        logging.info(f"Transaction found: {result}")
        return jsonify({"status": "success", "message": f"Transaction details: {result}"}), 200
    else:
        logging.warning(f"Transaction not found: {transaction_number}")
        return jsonify({"status": "error", "message": "Transaction not found."}), 404

def run_flask():
    logging.debug("Starting Flask server...")
    app.run(debug=True, host="0.0.0.0", use_reloader=False)  # Disable reloader to avoid thread conflicts

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    flask_thread.join()