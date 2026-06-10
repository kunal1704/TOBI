import base64
import os
from email.message import EmailMessage

from dotenv import load_dotenv


"""
Gmail Draft Service
-------------------

Creates Gmail drafts from generated outreach emails using the Gmail API.
Requires a Google OAuth client file at GMAIL_CREDENTIALS_FILE and stores
the user token at GMAIL_TOKEN_FILE.
"""


SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
DEFAULT_CREDENTIALS_FILE = "credentials.json"
DEFAULT_TOKEN_FILE = "token.json"
GMAIL_DRAFTS_URL = "https://mail.google.com/mail/u/0/#drafts"


def _load_google_imports():
    try:
        from google.auth.exceptions import RefreshError
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        return Request, Credentials, InstalledAppFlow, build, RefreshError

    except ImportError as exc:
        raise RuntimeError(
            "Gmail dependencies are missing. Install google-api-python-client, "
            "google-auth-httplib2, google-auth-oauthlib, and google-auth."
        ) from exc


def _get_gmail_service():
    load_dotenv()

    credentials_file = os.getenv("GMAIL_CREDENTIALS_FILE", DEFAULT_CREDENTIALS_FILE)
    token_file = os.getenv("GMAIL_TOKEN_FILE", DEFAULT_TOKEN_FILE)

    if not os.path.exists(credentials_file):
        raise FileNotFoundError(
            f"Google OAuth credentials file not found: {credentials_file}. "
            "Create an OAuth desktop client in Google Cloud, enable the Gmail API, "
            "download it as credentials.json, or set GMAIL_CREDENTIALS_FILE."
        )

    Request, Credentials, InstalledAppFlow, build, RefreshError = _load_google_imports()

    creds = None

    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        except ValueError:
            os.remove(token_file)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                # Google returns invalid_grant when the saved refresh token is
                # revoked, expired, or issued for changed OAuth settings.
                if os.path.exists(token_file):
                    os.remove(token_file)

                creds = None

        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def create_gmail_draft(to_email, subject, body):
    if not to_email:
        raise ValueError("Recipient email is required before saving a Gmail draft.")

    service = _get_gmail_service()

    message = EmailMessage()
    message["To"] = to_email
    message["Subject"] = subject

    message.set_content(body)

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft_body = {
        "message": {
            "raw": encoded_message
        }
    }

    draft = service.users().drafts().create(userId="me", body=draft_body).execute()
    draft["gmail_url"] = GMAIL_DRAFTS_URL

    return draft
