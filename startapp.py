from constant import generate_user_token, BaseUrl

def call_home():
    t = generate_user_token(5587470125)
    h = f"{BaseUrl}/?token={t}&demo=True"
    print(h)
    # return redirect(h)

call_home()