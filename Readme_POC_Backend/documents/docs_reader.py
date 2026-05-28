"""
Documents Reader Module
Fetches content from Google Docs using the Google Docs API.
"""

from googleapiclient.discovery import build
from auth.token_gen import get_credentials


class DocsReader:
    """Client for reading Google Docs documents."""
    
    def __init__(self):
        """Initialize Google Docs client with authenticated credentials."""
        creds = get_credentials()
        self.service = build('docs', 'v1', credentials=creds)
    
    def fetch_notes_text(self, doc_id: str) -> tuple[str, str]:
        """
        Fetch document content from Google Docs.
        
        Args:
            doc_id: Google Docs document ID
            
        Returns:
            tuple: (document_title, document_content)
        """
        try:
            # Fetch document
            document = self.service.documents().get(documentId=doc_id).execute()
            
            # Extract title
            title = document.get('title', 'Untitled Document')
            
            # Extract text content
            content = document.get('body', {}).get('content', [])
            text_content = self._extract_text_from_content(content)
            
            return (title, text_content)
            
        except Exception as error:
            print(f"Error reading document {doc_id}: {error}")
            return (None, None)
    
    def _extract_text_from_content(self, content_elements):
        """
        Recursively extract text from document content elements.
        
        Args:
            content_elements: List of content elements from Docs API
            
        Returns:
            str: Extracted text content
        """
        text_parts = []
        
        for element in content_elements:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                elements = paragraph.get('elements', [])
                
                for elem in elements:
                    if 'textRun' in elem:
                        text_parts.append(elem['textRun'].get('content', ''))
            
            elif 'table' in element:
                # Extract text from table cells
                table = element['table']
                for row in table.get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        cell_content = cell.get('content', [])
                        text_parts.append(self._extract_text_from_content(cell_content))
            
            elif 'sectionBreak' in element or 'pageBreak' in element:
                # Add line break for section/page breaks
                text_parts.append('\n')
        
        return ''.join(text_parts)
