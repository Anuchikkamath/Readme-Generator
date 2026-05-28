"""
Google OAuth Authentication Module
Handles OAuth flow and token management for Gmail and Docs APIs.
"""

import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes required for Gmail and Google Docs APIs
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/documents.readonly'
]

# Configuration - can be overridden via environment variables
# Get the directory of the current file (auth/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the project root (parent of auth/)
PROJECT_ROOT = os.path.dirname(BASE_DIR)

CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', os.path.join(BASE_DIR, 'a_new_cred.json'))
TOKEN_FILE = os.getenv('GOOGLE_TOKEN_FILE', os.path.join(PROJECT_ROOT, 'token.pickle'))


def get_credentials():
    """
    Get authenticated credentials, reusing token.pickle if available,
    or triggering OAuth flow if needed.
    
    Returns:
        google.oauth2.credentials.Credentials: Authenticated credentials
    """
    creds = None
    
    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid credentials, trigger OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired token
            creds.refresh(Request())
        else:
            # Start OAuth flow
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"Credentials file '{CREDENTIALS_FILE}' not found. "
                    "Please ensure credentials.json is present."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save token for future use
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds
