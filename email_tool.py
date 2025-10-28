from email.mime.text import MIMEText
import base64
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from typing import List
import pickle

class GmailAgentTool:
    def __init__(self, creds_path='token.pickle'):
        creds = pickle.load(open(creds_path, 'rb'))
        self.service = build('gmail', 'v1', credentials=creds)

    def send_email(self, to_addresses: List[str], subject: str, body: str):
        message = MIMEText(body)
        message['to'] = ', '.join(to_addresses)
        message['subject'] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        message_body = {'raw': raw}

        self.service.users().messages().send(userId='me', body=message_body).execute()

