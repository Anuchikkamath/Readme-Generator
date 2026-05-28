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

def force_nuke():
    print("=" * 60)
    print("FORCE NUKE CANCELED EVENT")
    print("=" * 60)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Explicitly drop the table shown in screenshot
        # The screenshot showed 'canceled_event'.
        # We will try a few variations just in case.
        tables_to_drop = ['canceled_event', 'canceled_events', 'cancelled_event', 'cancelled_events']
        
        for table in tables_to_drop:
            print(f"Attempting to drop table '{table}'...")
            try:
                cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
                print(f"  [OK] Dropped table '{table}' (if it existed)")
            except Exception as e:
                print(f"  [WARN] Could not drop '{table}': {e}")
                conn.rollback() # Reset transaction

        # 2. Cleanup metadata having 'cancel'
        print("\nCleaning up metadata...")
        cursor.execute("DELETE FROM projects_metadata WHERE normalized_name ILIKE '%cancel%' OR canonical_name ILIKE '%cancel%'")
        print(f"  [OK] Deleted {cursor.rowcount} row(s) from projects_metadata")

        # 3. Cleanup readmes having 'cancel'
        print("Cleaning up readmes...")
        cursor.execute("DELETE FROM project_readmes WHERE normalized_name ILIKE '%cancel%' OR project_name ILIKE '%cancel%'")
        print(f"  [OK] Deleted {cursor.rowcount} row(s) from project_readmes")
        
        conn.commit()
        print("\n[SUCCESS] Force cleanup complete.")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Failed: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    force_nuke()
