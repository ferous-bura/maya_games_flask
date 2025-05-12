import requests
from constant import BaseUrl, generate_user_token
telegram_id = "7831842753"

def get_token():
    return generate_user_token(7831842753)

def test_check_registration():
    """Test the check registration endpoint."""
    response = requests.post(f"{BaseUrl}/bot/check_registration", json={"telegram_id": telegram_id}, timeout=5)
    print("Check Registration Response:", response.json())

def test_transactions():
    """Test the transactions endpoint."""
    response = requests.get(f"{BaseUrl}/payment/transactions", params={"token": token}, timeout=5)
    if response.status_code == 200:
        try:
            print("Transactions Response:", response.json())
        except requests.exceptions.JSONDecodeError:
            print("Error: Response is not valid JSON.")
            print("Raw Response Content:", response.text)
    else:
        print(f"Error: Received status code {response.status_code}")
        print("Raw Response Content:", response.text)

def test_pending_deposits():
    """Test the pending deposits endpoint."""
    response = requests.post(f"{BaseUrl}/payment/pending_deposits", json={"telegram_id": telegram_id}, timeout=5)
    print("Pending Deposits Response:", response.json())

def test_payment():
    """Test the payment endpoint."""
    raw_message = "Dear BIRUH, your account 2*06 was credited with ETB 1,000.00 by A/R TELE BIRR. Available Balance:  ETB 1,057.07. Receipt: https://cs.bankofabyssinia.com/slip/?trx=FT25101WLPN010104 Feedback: https://cs.bankofabyssinia.com/cs/?trx=CFT25101WLPN0 For help, call 8397 (24/7 Toll-Free). Bank of Abyssinia."
    response = requests.post(f"{BaseUrl}/payment", json={"raw_message": raw_message, "telegram_id": telegram_id}, timeout=5)
    print("Payment Response:", response.json())

token = get_token()

if __name__ == "__main__":
    test_check_registration()
    # test_transactions()
    test_pending_deposits()
    test_payment()