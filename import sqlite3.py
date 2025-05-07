import sqlite3
import logging
import requests
from flask import Blueprint, request, jsonify, redirect, url_for
from .utils import TELEGRAM_BOT_TOKEN, update_user_balance

referral_blueprint = Blueprint('referral', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@referral_blueprint.route('/referral/generate', methods=['POST'])
def generate_referral_link():
    """Generate a unique referral link for the user."""
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    if not telegram_id:
        return jsonify({'status': 'error', 'message': 'Telegram ID required'}), 400
    
    try:
        with sqlite3.connect('transactions.db') as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user = c.fetchone()
            if not user:
                return jsonify({'status': 'error', 'message': 'User not found'}), 404
            user_id = user[0]
            referral_link = f"https://t.me/gamer_gr_bot?start=ref_{user_id}"
            return jsonify({'status': 'success', 'referral_link': referral_link})
    except sqlite3.Error as e:
        logging.error(f"Database error in generate_referral_link: {e}")
        return jsonify({'status': 'error', 'message': 'Database error'}), 500

@referral_blueprint.route('/referral/process', methods=['POST'])
def process_referral():
    """Process a referral when a new user joins via a referral link."""
    data = request.get_json()
    referee_telegram_id = data.get('telegram_id')
    referral_code = data.get('referral_code')  # e.g., ref_123
    
    if not referee_telegram_id or not referral_code:
        return jsonify({'status': 'error', 'message': 'Missing telegram_id or referral_code'}), 400
    
    try:
        with sqlite3.connect('transactions.db') as conn:
            c = conn.cursor()
            # Get referee user ID
            c.execute("SELECT id FROM users WHERE telegram_id = ?", (referee_telegram_id,))
            referee = c.fetchone()
            if not referee:
                return jsonify({'status': 'error', 'message': 'Referee not found'}), 404
            referee_id = referee[0]
            
            # Extract referrer ID from referral code
            if not referral_code.startswith('ref_'):
                return jsonify({'status': 'error', 'message': 'Invalid referral code'}), 400
            referrer_id = referral_code[4:]  # Remove 'ref_' prefix
            c.execute("SELECT id FROM users WHERE id = ?", (referrer_id,))
            referrer = c.fetchone()
            if not referrer or referrer_id == referee_id:
                return jsonify({'status': 'error', 'message': 'Invalid or self-referral'}), 400
            
            # Check if referee already has a referrer
            c.execute("SELECT id FROM referrals WHERE referee_id = ?", (referee_id,))
            if c.fetchone():
                return jsonify({'status': 'error', 'message': 'User already referred'}), 400
            
            # Record referral
            c.execute("INSERT INTO referrals (referrer_id, referee_id) VALUES (?, ?)", (referrer_id, referee_id))
            conn.commit()
            logging.info(f"Referral recorded: referrer_id={referrer_id}, referee_id={referee_id}")
            return jsonify({'status': 'success', 'message': 'Referral recorded'})
    except sqlite3.Error as e:
        logging.error(f"Database error in process_referral: {e}")
        return jsonify({'status': 'error', 'message': 'Database error'}), 500

@referral_blueprint.route('/referral/check_deposit', methods=['POST'])
def check_deposit():
    """Check if referee made a deposit and issue rewards."""
    data = request.get_json()
    referee_telegram_id = data.get('telegram_id')
    
    try:
        with sqlite3.connect('transactions.db') as conn:
            c = conn.cursor()
            # Get referee user ID
            c.execute("SELECT id FROM users WHERE telegram_id = ?", (referee_telegram_id,))
            referee = c.fetchone()
            if not referee:
                return jsonify({'status': 'error', 'message': 'User not found'}), 404
            referee_id = referee[0]
            
            # Check for verified deposit
            c.execute("SELECT id FROM transactions WHERE user_id = ? AND verified = TRUE AND status = 'verified'", (referee_id,))
            if not c.fetchone():
                return jsonify({'status': 'success', 'message': 'No verified deposit yet'})
            
            # Check if referral reward already issued
            c.execute("SELECT referrer_id, reward_issued FROM referrals WHERE referee_id = ? AND reward_issued = FALSE", (referee_id,))
            referral = c.fetchone()
            if not referral:
                return jsonify({'status': 'success', 'message': 'No pending rewards'})
            
            referrer_id, _ = referral
            reward_amount = 10.0  # Bonus for both referrer and referee
            
            # Update balances
            update_user_balance(referrer_id, reward_amount)
            update_user_balance(referee_id, reward_amount)
            
            # Mark reward as issued
            c.execute("UPDATE referrals SET reward_issued = TRUE, reward_amount = ? WHERE referee_id = ?", (reward_amount, referee_id))
            conn.commit()
            logging.info(f"Referral rewards issued: referrer_id={referrer_id}, referee_id={referee_id}, amount={reward_amount}")
            return jsonify({'status': 'success', 'message': 'Rewards issued'})
    except sqlite3.Error as e:
        logging.error(f"Database error in check_deposit: {e}")
        return jsonify({'status': 'error', 'message': 'Database error'}), 500

@referral_blueprint.route('/referral/post_story', methods=['POST'])
def post_story():
    """Post a Telegram story with a promotional image and link."""
    data = request.get_json()
    telegram_id = data.get('telegram_id')
    
    try:
        with sqlite3.connect('transactions.db') as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user = c.fetchone()
            if not user:
                return jsonify({'status': 'error', 'message': 'User not found'}), 404
            user_id = user[0]
            
        # Telegram story API request
        story_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendStory"
        story_data = {
            'chat_id': '@YourChannelOrGroup',  # Replace with your channel or group ID
            'media': {
                'type': 'photo',
                'media': 'https://yourdomain.com/static/promo_image.jpg',  # Replace with actual image URL
                'caption': 'Join Game Hub and play exciting games like Keno, Bingo, Ludo, and Spin! 🎮 Use this link to get started: https://t.me/gamer_gr_bot?start=ref_' + str(user_id)
            }
        }
        response = requests.post(story_url, json=story_data)
        if response.status_code == 200:
            logging.info(f"Story posted for user_id={user_id}")
            return jsonify({'status': 'success', 'message': 'Story posted'})
        else:
            logging.error(f"Failed to post story: {response.text}")
            return jsonify({'status': 'error', 'message': 'Failed to post story'}), 500
    except Exception as e:
        logging.error(f"Error in post_story: {e}")
        return jsonify({'status': 'error', 'message': 'Server error'}), 500
