"""
Body Parser Module
Parses email body to extract Google Docs document IDs and HTML content.
"""

import re
import base64


class BodyParser:
    """Parser for email body content."""
    
    def get_html_body(self, message):
        """
        Recursively extract HTML body content from email MIME parts.
        
        Args:
            message: Gmail message object
            
        Returns:
            str: HTML content of the email, or empty string if not found
        """
        payload = message.get('payload', {})
        html_content = ""
        
        def extract_html(part):
            """Recursively extract HTML from email parts."""
            html = ""
            
            mime_type = part.get('mimeType', '')
            
            if mime_type == 'text/html':
                data = part.get('body', {}).get('data', '')
                if data:
                    try:
                        # Decode base64url content
                        decoded = base64.urlsafe_b64decode(data)
                        html = decoded.decode('utf-8', errors='ignore')
                    except Exception as e:
                        print(f"    Warning: Error decoding HTML part: {e}")
            
            # Check for nested parts (multipart messages)
            if 'parts' in part:
                for subpart in part['parts']:
                    html += extract_html(subpart)
            
            return html
        
        html_content = extract_html(payload)
        return html_content
    
    def get_plain_text_body(self, message):
        """
        Recursively extract plain text body content from email MIME parts.
        
        Args:
            message: Gmail message object
            
        Returns:
            str: Plain text content of the email, or empty string if not found
        """
        payload = message.get('payload', {})
        text_content = ""
        
        def extract_text(part):
            """Recursively extract plain text from email parts."""
            text = ""
            
            mime_type = part.get('mimeType', '')
            
            if mime_type == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    try:
                        # Decode base64url content
                        decoded = base64.urlsafe_b64decode(data)
                        text = decoded.decode('utf-8', errors='ignore')
                    except Exception as e:
                        print(f"    Warning: Error decoding text part: {e}")
            
            # Check for nested parts (multipart messages)
            if 'parts' in part:
                for subpart in part['parts']:
                    text += extract_text(subpart)
            
            return text
        
        text_content = extract_text(payload)
        return text_content
    
    def extract_notes_doc_id(self, message):
        """
        Parse email body (HTML and plain text) for Google Docs URLs and extract document ID.
        
        Supports multiple URL formats:
        - https://docs.google.com/document/d/DOC_ID
        - https://docs.google.com/document/u/0/d/DOC_ID
        - https://docs.google.com/document/u/1/d/DOC_ID
        
        Args:
            message: Gmail message object
            
        Returns:
            str: First document ID found, or None if no document ID is found
        """
        # Robust regex pattern that handles all Google Docs URL formats
        # Matches: /d/DOC_ID or /u/0/d/DOC_ID or /u/1/d/DOC_ID
        docs_pattern = r"https://docs\.google\.com/document/(?:u/\d+/)?d/([a-zA-Z0-9_-]+)"
        
        # Try HTML body first
        html_content = self.get_html_body(message)
        if html_content:
            matches = re.findall(docs_pattern, html_content)
            if matches:
                doc_id = matches[0]
                print(f"    [DEBUG] Extracted doc_id from HTML: {doc_id}")
                return doc_id
            else:
                print(f"    [DEBUG] No doc_id found in HTML body (length: {len(html_content)})")
        
        # Fallback to plain text body
        text_content = self.get_plain_text_body(message)
        if text_content:
            matches = re.findall(docs_pattern, text_content)
            if matches:
                doc_id = matches[0]
                print(f"    [DEBUG] Extracted doc_id from plain text: {doc_id}")
                return doc_id
            else:
                print(f"    [DEBUG] No doc_id found in plain text body (length: {len(text_content)})")
        
        # If neither HTML nor plain text had content
        if not html_content and not text_content:
            print(f"    [DEBUG] Extraction failed: No HTML or plain text body found in email")
        else:
            print(f"    [DEBUG] Extraction failed: No Google Docs URL found in email body")
        
        return None
