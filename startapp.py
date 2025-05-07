from flask import redirect
import requests
from utils import BaseUrl, generate_user_token

def call_home():
    t = generate_user_token(7831842753)
    h = f"{BaseUrl}/?token={t}&demo=True"
    print(h)
    # return redirect(h)

call_home()