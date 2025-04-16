import time
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os

# If modifying these SCOPES, delete token.json first.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# With this:
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']  # Allows read/write

# OR (better) use path joining:
import os
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), 'credentials.json')
flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If no valid credentials, let the user log in.
    if not creds or not creds.valid:
        # flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def listen_for_emails():
    service = get_gmail_service()
    print("Listening for new emails...")
    
    while True:
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread").execute()
        messages = results.get('messages', [])
        
        if messages:
            for msg in messages:
                email = service.users().messages().get(userId='me', id=msg['id']).execute()
                headers = email['payload']['headers']
                subject = next(h['value'] for h in headers if h['name'] == 'Subject')
                sender = next(h['value'] for h in headers if h['name'] == 'From')
                print(f"New email from {sender}: {subject}")
                
                # Mark as read (optional)
                # service.users().messages().modify(userId='me', id=msg['id'], body={'removeLabelIds': ['UNREAD']}).execute()
        
        time.sleep(10)  # Check every minute

if __name__ == '__main__':
    listen_for_emails()