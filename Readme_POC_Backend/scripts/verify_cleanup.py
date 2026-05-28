import sys
import os
import psycopg2
from dotenv import load_dotenv

# Add parent directory to path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

load_dotenv()

def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'projects')
    )

def verify_nuke():
    print("=" * 60)
    print("VERIFY CLEANUP")
    print("=" * 60)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check metadata
        cursor.execute("SELECT count(*) FROM projects_metadata WHERE canonical_name ILIKE '%cancel%' OR normalized_name ILIKE '%cancel%'")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("[PASS] No cancelled projects in metadata.")
        else:
            print(f"[FAIL] Found {count} cancelled projects in metadata.")
            
        # Check tables (query information_schema)
        cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_name ILIKE '%cancel%' AND table_schema = 'public'")
        table_count = cursor.fetchone()[0]
        
        if table_count == 0:
            print("[PASS] No cancelled project tables found.")
        else:
            print(f"[FAIL] Found {table_count} tables with 'cancel' in name.")

    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    verify_nuke()
