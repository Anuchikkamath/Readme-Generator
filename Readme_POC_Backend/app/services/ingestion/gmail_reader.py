"""
Gmail Reader Module
Fetches emails from Gmail API and extracts message details.
"""

from typing import List, Optional
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


class GmailReader:
    """Client for reading emails from Gmail API."""
    
    def __init__(self, access_token: str):
        """
        Initialize Gmail client with user's access token.
        
        Args:
            access_token: User's OAuth access token for Gmail API
        """
        # Create credentials from access token
        creds = Credentials(token=access_token)
        self.service = build('gmail', 'v1', credentials=creds)
    
    def get_all_emails(self, query='Notes:', limit=None):
        """
        Fetch ALL emails matching the query filter using pagination.
        
        Args:
            query (str): Gmail search query (default: 'Notes:')
            
        Returns:
            list: List of email message objects
        """
        try:
            all_messages = []
            page_token = None
            page_num = 0
            
            # Fetch all emails using pagination
            while True:  # existing code continues...
                page_num += 1
                # Prepare request parameters
                request_params = {
                    'userId': 'me',
                    'q': query,
                    'maxResults': 500  # Maximum allowed by Gmail API
                }
                
                if page_token:
                    request_params['pageToken'] = page_token
                
                # Search for messages
                results = self.service.users().messages().list(**request_params).execute()
                
                messages = results.get('messages', [])
                result_size_estimate = results.get('resultSizeEstimate', 0)
                
                print(f"  Page {page_num}: Found {len(messages)} messages (estimated total: {result_size_estimate})")
                
                if not messages:
                    break
                
                # Fetch full message details
                fetched_count = 0
                for msg in messages:
                    try:
                        message = self.service.users().messages().get(
                            userId='me',
                            id=msg['id']
                        ).execute()
                        all_messages.append(message)
                        fetched_count += 1
                    except Exception as e:
                        print(f"    Error fetching message {msg['id']}: {e}")
                        continue
                    
                    if limit and len(all_messages) >= limit:
                        print(f"    [DEBUG] Reached limit of {limit} messages")
                        break
                
                print(f"    Successfully fetched {fetched_count}/{len(messages)} message details")
                
                if limit and len(all_messages) >= limit:
                    break
                
                # Check if there are more pages
                page_token = results.get('nextPageToken')
                if not page_token:
                    print(f"  No more pages to fetch")
                    break
                else:
                    print(f"  More pages available, continuing...")
            
            
            print(f"[OK] Total emails fetched: {len(all_messages)}")
            return all_messages
            
        except Exception as error:
            print(f"[ERROR] Error fetching emails: {error}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_message_details(self, message_id):
        """
        Fetch full message details including body and headers.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            dict: Complete message object
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            return message
        except Exception as e:
            print(f"Error fetching message {message_id}: {e}")
            return None
    
    def get_subject(self, message):
        """
        Extract subject line from message headers.
        
        Args:
            message: Gmail message object
            
        Returns:
            str: Subject line or empty string if not found
        """
        headers = message.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'].lower() == 'subject':
                return header['value']
        return ''
    
    def get_date(self, message):
        """
        Extract the email date from message headers and return as YYYY-MM-DD.
        
        Tries the 'Date' header first, then falls back to Gmail's internalDate
        (epoch milliseconds).
        
        Args:
            message: Gmail message object
            
        Returns:
            str: Date in YYYY-MM-DD format, or None if not found
        """
        from datetime import datetime
        from email.utils import parsedate_to_datetime
        
        # Strategy 1: Parse the 'Date' header (e.g. "Mon, 10 Feb 2025 14:30:00 +0530")
        headers = message.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'].lower() == 'date':
                try:
                    dt = parsedate_to_datetime(header['value'])
                    return dt.strftime('%Y-%m-%d')
                except Exception:
                    pass
        
        # Strategy 2: Use Gmail's internalDate (epoch milliseconds)
        internal_date = message.get('internalDate')
        if internal_date:
            try:
                dt = datetime.fromtimestamp(int(internal_date) / 1000)
                return dt.strftime('%Y-%m-%d')
            except Exception:
                pass
        
        return None

    def is_notes_mail(self, message):
        """
        Check if email subject starts with "Notes:".
        
        Args:
            message: Gmail message object
            
        Returns:
            bool: True if subject starts with "Notes:"
        """
        subject = self.get_subject(message)
        return subject.lower().startswith('notes:')

    def extract_participants(self, message: dict) -> List[str]:
        """
        Extract unique email addresses from From, To, Cc, and Bcc headers.
        
        Args:
            message: Gmail message object
            
        Returns:
            list: List of unique email addresses
        """
        import re
        headers = message.get('payload', {}).get('headers', [])
        participants = set()
        
        # Regex for extracting emails from "Name <email@example.com>" or "email@example.com"
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        
        target_headers = ['from', 'to', 'cc', 'bcc']
        for header in headers:
            if header['name'].lower() in target_headers:
                value = header['value']
                found = re.findall(email_pattern, value)
                for email in found:
                    participants.add(email.lower())
        
        return list(participants)

    def get_full_metadata(self, message: dict) -> dict:
        """
        Gather all relevant metadata requested by the user.
        
        Args:
            message: Gmail message object
            
        Returns:
            dict: Metadata including ID, threadId, snippet, and participants
        """
        return {
            "id": message.get("id"),
            "threadId": message.get("threadId"),
            "labelIds": message.get("labelIds"),
            "snippet": message.get("snippet"),
            "historyId": message.get("historyId"),
            "internalDate": message.get("internalDate"),
            "participants": self.extract_participants(message),
            "subject": self.get_subject(message),
            "date": self.get_date(message)
        }
