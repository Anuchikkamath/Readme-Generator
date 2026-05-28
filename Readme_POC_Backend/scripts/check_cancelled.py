import sys
import os

# Add parent directory to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

from app.services.storage.postgres_client import PostgresClient

def check_cancelled():
    client = PostgresClient()
    tables = client.list_project_tables()
    
    conn = client.get_connection()
    cursor = conn.cursor()
    
    found_count = 0
    
    for table in tables:
        try:
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
            
            if target_col:
                query = f'SELECT COUNT(*) FROM "{table}" WHERE "{target_col}" ILIKE %s OR "{target_col}" ILIKE %s'
                cursor.execute(query, ('%Canceled%', '%Cancelled%'))
                count = cursor.fetchone()[0]
                if count > 0:
                    print(f"Found {count} cancelled meetings in '{table}'")
                    found_count += count
        except Exception:
            pass
            
    cursor.close()
    conn.close()
    
    if found_count == 0:
        print("VERIFICATION PASS: No cancelled meetings found.")
    else:
        print(f"VERIFICATION FAIL: Found {found_count} cancelled meetings.")

if __name__ == "__main__":
    check_cancelled()
