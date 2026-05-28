"""
Main Pipeline Script
Processes Gmail emails, extracts meeting notes, and stores them in PostgreSQL.
Groups emails by project and processes each project independently.
"""

import sys
import os
from collections import defaultdict
from datetime import datetime

# Add parent directory and app/services to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, 'app', 'services'))

from ingestion.gmail_reader import GmailReader
from ingestion.body_parser import BodyParser
from documents.docs_reader import DocsReader
from llm.ollama_client import LLMClient
from storage.postgres_client import PostgresClient
from project_resolver import ProjectResolver


def main():
    """Main pipeline execution."""
    print("=" * 60)
    print("Multi-Project Meeting Notes Processing Pipeline")
    print("=" * 60)
    
    try:
        # Initialize clients
        print("\n[1/6] Initializing clients...")
        gmail_reader = GmailReader()
        body_parser = BodyParser()
        docs_reader = DocsReader()
        llm_client = LLMClient()
        postgres_client = PostgresClient()
        project_resolver = ProjectResolver()
        
        # Fetch emails
        print("\n[2/6] Fetching emails with 'Notes:' query...")
        emails = gmail_reader.get_all_emails(query='Notes:')
        
        if not emails:
            print("No emails found.")
            return
        
        print(f"[OK] Fetched {len(emails)} emails")
        
        # Group emails by subject (will be resolved to canonical projects during processing)
        print("\n[3/6] Preparing emails for processing...")
        email_list = []
        
        for email in emails:
            subject = gmail_reader.get_subject(email)
            email_list.append({
                'email': email,
                'subject': subject
            })
        
        print(f"[OK] Prepared {len(email_list)} email(s) for processing")
        
        # Process each email (canonical projects resolved automatically)
        print("\n[4/6] Processing emails...")
        total_processed = 0
        total_skipped = 0
        total_stored = 0
        
        for idx, email_data in enumerate(email_list, 1):
            email = email_data['email']
            subject = email_data['subject']
            
            print(f"\n  [Email {idx}/{len(email_list)}] {subject}")
            
            
            # Check for cancellation
            if 'canceled' in subject.lower() or 'cancelled' in subject.lower():
                print(f"    [SKIP] Meeting is canceled: {subject}")
                total_skipped += 1
                continue

            # Extract document ID
            doc_id = body_parser.extract_notes_doc_id(email)
                
            if not doc_id:
                print(f"    [WARN] No Google Docs link found, skipping...")
                total_skipped += 1
                continue
            
            # Fetch document content
            try:
                print(f"    -> Fetching document: {doc_id}")
                title, content = docs_reader.fetch_notes_text(doc_id)
                
                if not content:
                    print(f"    [ERROR] Failed to read document content")
                    total_skipped += 1
                    continue
                
                print(f"    [OK] Document read: {title} ({len(content)} characters)")
                
            except Exception as e:
                print(f"    [ERROR] Error reading document: {e}")
                total_skipped += 1
                continue
            
            # Extract email date for meeting_date
            email_date = gmail_reader.get_date(email)
            if email_date:
                print(f"    [OK] Email date: {email_date}")
            
            # Extract structured data using LLM
            try:
                print(f"    -> Sending to LLM for extraction...")
                structured_data = llm_client.extract_structured_data(content, meeting_date=email_date)
                
                # Get LLM-extracted project name if available
                llm_project = structured_data.get('project_name')
                
                print(f"    [OK] LLM extraction complete")
                print(f"      Date: {structured_data.get('meeting_date', 'N/A')}")
                if llm_project:
                    print(f"      LLM Project: {llm_project}")
                
            except Exception as e:
                print(f"    [ERROR] Error in LLM extraction: {e}")
                total_skipped += 1
                continue
            
            # Store in database (uses canonical project resolution)
            try:
                # Resolve canonical project and store
                postgres_client.insert_meeting_note(
                    email_subject=subject,
                    data=structured_data,
                    llm_extracted_project=llm_project
                )
                total_stored += 1
                total_processed += 1
                print(f"    [OK] Stored in database")
                
            except Exception as e:
                print(f"    [ERROR] Error storing in database: {e}")
                total_skipped += 1
                continue
        
        # Final summary
        print(f"\n{'=' * 60}")
        print(f"[5/6] Pipeline Summary")
        print(f"{'=' * 60}")
        print(f"Total emails fetched:        {len(emails)}")
        print(f"Total meetings stored:        {total_stored}")
        print(f"Successfully processed:       {total_processed}")
        print(f"Skipped/failed:              {total_skipped}")
        print(f"{'=' * 60}")
        
        # List all canonical projects
        print(f"\n[6/6] Registered Canonical Projects:")
        projects = postgres_client.get_all_projects()
        if projects:
            for canonical, normalized in projects:
                print(f"  - {canonical} -> table: {normalized}")
        else:
            print("  No projects registered yet.")
        
        if total_skipped > 0:
            print(f"\n[WARN] Note: Some emails were skipped. Check logs above for details.")
        
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.")
        sys.exit(1)
    except Exception as error:
        print(f"\n\nError in pipeline: {error}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
