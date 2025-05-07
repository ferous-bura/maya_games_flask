import requests

BaseUrl = "http://127.0.0.1:8000"
def set_manual_flag(receipt_id, amount, payer_name, payer_phone_last4, game_user_id=None):
    url = "{BaseUrl}/manual/flag"
    payload = {
        "receipt_id": receipt_id,
        "amount": amount,
        "payer_name": payer_name,
        "payer_phone_last4": payer_phone_last4,
        "game_user_id": game_user_id
    }
    headers = {"X-API-Key": "your-secret-key", "Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200 and response.json().get("flag") == "green":
        print(f"Payment verified for {payer_name}: {amount}")
        # Notify game server to credit user
        return True
    print(f"Error: {response.json().get('error')}")
    return False

# Example usage
# set_manual_flag(
#     receipt_id="MANUAL123",
#     amount="1000.00 Birr",
#     payer_name="John Doe",
#     payer_phone_last4="1234",
#     game_user_id="user123"
# )


def verify_cbe_receipt(receipt_id):
    url = f"{BaseUrl}/extract/cbe?id={receipt_id}"
    headers = {"X-API-Key": "251f0f6ad923f82749b30a2ee1f378d1"}
    response = requests.get(url, headers=headers)
    print(response)
    return response.json()

def verify_boa_receipt(receipt_id):
    url = f"{BaseUrl}/extract/boa?trx={receipt_id}"
    headers = {"X-API-Key": "251f0f6ad923f82749b30a2ee1f378d1"}
    response = requests.get(url, headers=headers)
    return response.json()

def verify_telebirr_receipt(receipt_id):
    url = f"{BaseUrl}/extract/telebirr?receipt_id={receipt_id}"
    headers = {"X-API-Key": "251f0f6ad923f82749b30a2ee1f378d1"}
    response = requests.get(url, headers=headers)
    return response.json()

# v = verify_cbe_receipt("FT25101CWSJC50029015")
# v = verify_boa_receipt("FT25100DX5R660206")
# v = verify_telebirr_receipt("CD90N1PKKG")
# print(v)

"""
curl -X GET "{BaseUrl}/extract/telebirr?receipt_id=CD90N1PKKG" -H "X-API-Key: 251f0f6ad923f82749b30a2ee1f378d1"


curl -X POST http://localhost:5000/manual/flag \
-H "X-API-Key: your-secret-key" \
-H "Content-Type: application/json" \
-d '{"receipt_id":"MANUAL123","amount":"1000.00 Birr","payer_name":"John Doe","payer_phone_last4":"1234","game_user_id":"user123"}'


"""