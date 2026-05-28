import sys
import os

# Add parent directory to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

from app.services.storage.postgres_client import PostgresClient

def cleanup_cancelled_meetings():
    print("=" * 60)
    print("Cleanup Cancelled Meetings Script")
    print("=" * 60)

    try:
        client = PostgresClient()
        tables = client.list_project_tables()
        
        print(f"Found {len(tables)} project tables.")
        
        total_deleted = 0
        
        conn = client.get_connection()
        cursor = conn.cursor()
        
        for table in tables:
            try:
                # Check if table has 'title' or 'email_subject' or similar column to check for cancellation
                # Based on previous analysis, data is stored in project tables. 
                # We need to know the schema. Project tables are dynamically created.
                # However, typically they have a 'title' or 'subject' from the meeting data.
                # Let's check columns first.
                
                cursor.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s AND table_schema = 'public'
                """, (table,))
                columns = [row[0].lower() for row in cursor.fetchall()]
                
                target_col = None
                if 'title' in columns:
                    target_col = 'title'
                elif 'subject' in columns:
                    target_col = 'subject'
                elif 'meeting_title' in columns:
                    target_col = 'meeting_title'
                
                if not target_col:
                    print(f"  [SKIP] Table '{table}' has no recognizable title/subject column.")
                    continue
                
                # Perform deletion
                # Using ILIKE for case-insensitive matching
                query = f'DELETE FROM "{table}" WHERE "{target_col}" ILIKE %s OR "{target_col}" ILIKE %s'
                cursor.execute(query, ('%Canceled%', '%Cancelled%'))
                
                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    print(f"  [CLEANUP] Deleted {deleted_count} record(s) from '{table}'")
                    total_deleted += deleted_count
                    conn.commit()
                else:
                    # print(f"  [OK] No cancelled meetings in '{table}'")
                    pass
                    
            except Exception as e:
                print(f"  [ERROR] Failed to process table '{table}': {e}")
                conn.rollback()
        
        print("-" * 60)
        print(f"Total cancelled meetings deleted: {total_deleted}")
        print("=" * 60)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"[ERROR] Script failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    cleanup_cancelled_meetings()
