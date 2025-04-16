import os
import sqlite3
import time
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from bs4 import BeautifulSoup  # For parsing HTML emails

# Database setup
def init_db():
    conn = sqlite3.connect('emails.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS emails
                 (id TEXT PRIMARY KEY, sender TEXT, subject TEXT, body TEXT, date TEXT)''')
    conn.commit()
    return conn

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
ALLOWED_SENDERS = ['biruhalex@gmail.com', 'another@example.com']

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def extract_email_body(payload):
    """Extracts plain text from email payload"""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                return part['body']['data']
    return payload['body']['data']

def save_email_to_db(conn, email_data):
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO emails VALUES (?, ?, ?, ?, ?)",
                  (email_data['id'], email_data['from'], email_data['subject'],
                   email_data['body'], email_data['date']))
        conn.commit()
        print(f"Saved email from {email_data['from']}")
    except sqlite3.Error as e:
        print(f"Database error: {e}")

def listen_for_emails():
    conn = init_db()
    service = get_gmail_service()
    print("Listening for new emails from allowed senders...")
    
    while True:
        try:
            # Search for unread emails from allowed senders
            query = "is:unread from:{}".format(" OR ".join(ALLOWED_SENDERS))
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=5
            ).execute()
            
            messages = results.get('messages', [])
            
            if messages:
                for msg in messages:
                    email = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    headers = {h['name']: h['value'] for h in email['payload']['headers']}
                    
                    if headers.get('From') not in ALLOWED_SENDERS:
                        continue
                    
                    # Decode email body
                    body_data = extract_email_body(email['payload'])
                    body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                    
                    # Save to database
                    email_data = {
                        'id': msg['id'],
                        'from': headers.get('From'),
                        'subject': headers.get('Subject'),
                        'body': body,
                        'date': headers.get('Date')
                    }
                    save_email_to_db(conn, email_data)
            
                # Mark as read (optional)
                # service.users().messages().modify(userId='me', id=msg['id'], body={'removeLabelIds': ['UNREAD']}).execute()
        
            time.sleep(10)  # Check every minute
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(300)  # Wait longer if error occurs

if __name__ == '__main__':
    import base64  # For email body decoding
    listen_for_emails()



"""
to view email address

import sqlite3
conn = sqlite3.connect('emails.db')
for row in conn.execute("SELECT * FROM emails"):
    print(row)
conn.close()

"""