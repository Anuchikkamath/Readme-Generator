"""
Main Pipeline Script
Processes Gmail emails, extracts meeting notes, and stores them in PostgreSQL.
Groups emails by project and processes each project independently.
"""

import sys
import os
from typing import Dict, Optional, Any, List
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.ingestion.gmail_reader import GmailReader
from app.services.ingestion.body_parser import BodyParser
from documents.docs_reader import DocsReader
from app.services.llm.ollama_client import LLMClient
from app.services.storage.postgres_client import PostgresClient
from app.services.project_resolver import ProjectResolver


def _extract_email_datetime(email: dict):
    """Best-effort extraction of email datetime for incremental sync."""
    internal_date = email.get('internalDate')
    if internal_date:
        try:
            return datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
        except Exception:
            pass

    headers = email.get('payload', {}).get('headers', [])
    for header in headers:
        if header.get('name', '').lower() == 'date':
            try:
                dt = parsedate_to_datetime(header.get('value'))
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
    return None


def sync(current_user: dict, user_id: str) -> Dict[str, Any]:
    """
    Execute the sync pipeline for a specific user.
    This function wraps the pipeline logic for API calls.
    
    Args:
        current_user: Current user dictionary with access_token
        user_id: User's UUID for data isolation
    
    Returns:
        dict: Status and summary of the sync operation
    """
    try:
        # Initialize clients with user's access token
        gmail_reader = GmailReader(access_token=current_user.get('access_token'))
        body_parser = BodyParser()
        docs_reader = DocsReader()
        llm_client = LLMClient()
        postgres_client = PostgresClient()
        project_resolver = ProjectResolver()

        # Fetch only emails after the user's last sync timestamp
        last_synced_at = postgres_client.get_user_last_synced_at(user_id)
        if last_synced_at and last_synced_at.tzinfo is None:
            last_synced_at = last_synced_at.replace(tzinfo=timezone.utc)
        query = 'Notes:'
        if last_synced_at:
            query = f"Notes: after:{int(last_synced_at.timestamp())}"

        emails = gmail_reader.get_all_emails(query=query)
        
        if not emails:
            return {
                "status": "up_to_date",
                "message": "Notes are already synced and up to date",
                "emails_fetched": 0,
                "new_emails": 0,
                "meetings_stored": 0,
                "processed": 0,
                "skipped": 0
            }
        
        # Prepare emails for processing
        email_list = []
        skipped_non_notes = 0
        for email in emails:
            # Check strict "Notes:" requirement
            if not gmail_reader.is_notes_mail(email):
                skipped_non_notes += 1
                continue
                
            subject = gmail_reader.get_subject(email)
            participants = gmail_reader.extract_participants(email)
            metadata = gmail_reader.get_full_metadata(email)
            
            print(f"[DEBUG] Processing Email: {subject}")
            print(f"  - Participants: {', '.join(participants)}")
            print(f"  - Msg ID: {metadata['id']}")
            
            email_list.append({
                'email': email,
                'subject': subject,
                'participants': participants,
                'message_id': metadata.get('id')
            })
        
        if skipped_non_notes:
            print(f"[INFO] Skipped {skipped_non_notes} emails not starting with 'Notes:'")
        
        if not email_list:
            return {
                "status": "up_to_date",
                "message": "Notes are already synced and up to date",
                "emails_fetched": len(emails),
                "new_emails": 0,
                "meetings_stored": 0,
                "processed": 0,
                "skipped": 0
            }

        # Process each email from incremental Gmail fetch.
        # Duplicate protection is handled by unique gmail_message_id in emails table.
        total_processed = 0
        total_skipped = 0
        total_stored = 0
        new_emails = 0
        latest_email_dt = last_synced_at
        
        for idx, email_data in enumerate(email_list, 1):
            email = email_data['email']
            subject = email_data['subject']
            participants = email_data['participants']
            message_id = email_data.get('message_id')
            email_dt = _extract_email_datetime(email)

            if not message_id:
                total_skipped += 1
                continue

            # Persist raw email for dedupe and audit trail
            email_body = body_parser.get_plain_text_body(email)
            inserted = postgres_client.insert_email_if_new(
                user_id=user_id,
                gmail_message_id=message_id,
                subject=subject,
                body=email_body,
                email_date=email_dt
            )
            if not inserted:
                # Duplicate (or failed insert), skip processing to avoid re-sync behavior
                total_skipped += 1
                continue

            new_emails += 1
            if email_dt and (latest_email_dt is None or email_dt > latest_email_dt):
                latest_email_dt = email_dt
            
            # Skip calendar notifications
            lower_subject = subject.lower()
            if any(x in lower_subject for x in ['Canceled event', 'declined:', 'accepted:', 'tentatively accepted:', 'updated invitation:']):
                print(f"    [INFO] Skipping calendar notification: {subject}")
                total_skipped += 1
                continue

            # Extract document ID
            doc_id = body_parser.extract_notes_doc_id(email)
            content = None
            
            if doc_id:
                # Fetch document content
                try:
                    title, content = docs_reader.fetch_notes_text(doc_id)
                    if not content:
                        print(f"    [WARNING] Document {doc_id} content is empty")
                except Exception as e:
                    print(f"    [ERROR] Failed to fetch document {doc_id}: {e}")
            
            # Fallback: If no doc_id or doc fetch failed, use email body
            if not content:
                print(f"    [INFO] No Doc ID or empty content. Using email body as fallback.")
                content = body_parser.get_plain_text_body(email)

            if not content:
                print(f"    [WARNING] No content found in email (Doc or Body). Skipping.")
                total_skipped += 1
                continue

            # Extract email date for meeting_date
            email_date = gmail_reader.get_date(email)
            
            # Extract structured data using LLM
            try:
                structured_data = llm_client.extract_structured_data(content, meeting_date=email_date)
                llm_project = structured_data.get('project_name')
                
                # Double check if LLM extracted "Canceled event" as title
                if llm_project and 'Canceled event' in llm_project.lower():
                     print(f"    [INFO] Skipping project with invalid name: {llm_project}")
                     total_skipped += 1
                     continue
                
            except Exception as e:
                print(f"    [ERROR] LLM extraction failed for {doc_id}: {e}")
                total_skipped += 1
                continue
            
            # Store in database (uses canonical project resolution)
            try:
                postgres_client.insert_meeting_note(
                    email_subject=subject,
                    data=structured_data,
                    llm_extracted_project=llm_project,
                    user_id=user_id,
                    participants=participants
                )
                total_stored += 1
                total_processed += 1
                
            except Exception as e:
                print(f"    [ERROR] Database insertion failed: {e}")
                total_skipped += 1
                continue

        if new_emails == 0:
            return {
                "status": "up_to_date",
                "message": "Notes are already synced and up to date",
                "emails_fetched": len(emails),
                "new_emails": 0,
                "meetings_stored": 0,
                "processed": 0,
                "skipped": total_skipped
            }

        if latest_email_dt:
            postgres_client.update_user_last_synced_at(user_id, latest_email_dt)
        
        return {
            "status": "synced",
            "message": "Gmail notes synced successfully",
            "emails_fetched": len(emails),
            "new_emails": new_emails,
            "meetings_stored": total_stored,
            "processed": total_processed,
            "skipped": total_skipped
        }
        
    except Exception as error:
        return {
            "status": "sync failed",
            "error": str(error)
        }
