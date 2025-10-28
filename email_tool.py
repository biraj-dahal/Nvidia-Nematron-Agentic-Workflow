from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from typing import List, Optional
import pickle

class GmailAgentTool:
    def __init__(self, creds_path='token.pickle'):
        creds = pickle.load(open(creds_path, 'rb'))
        self.service = build('gmail', 'v1', credentials=creds)

    def send_email(self, to_addresses: List[str], subject: str, body: str, html_body: Optional[str] = None):
        """Send email with optional HTML formatting

        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject line
            body: Plain text body (fallback for non-HTML clients)
            html_body: Optional HTML formatted body
        """
        if html_body:
            # Create multipart message for HTML
            message = MIMEMultipart('alternative')
            message['to'] = ', '.join(to_addresses)
            message['subject'] = subject

            # Attach plain text and HTML versions
            part1 = MIMEText(body, 'plain')
            part2 = MIMEText(html_body, 'html')
            message.attach(part1)
            message.attach(part2)
        else:
            # Plain text only
            message = MIMEText(body)
            message['to'] = ', '.join(to_addresses)
            message['subject'] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        message_body = {'raw': raw}

        self.service.users().messages().send(userId='me', body=message_body).execute()

