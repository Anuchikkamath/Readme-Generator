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
        database=os.getenv('DB_NAME', 'project')
    )

def nuke_cancelled_projects():
    print("=" * 60)
    print("NUKE CANCELLED PROJECTS")
    print("=" * 60)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Find projects that look like "Canceled event"
        print("Searching for project metadata...")
        cursor.execute("SELECT canonical_name, normalized_name FROM projects_metadata")
        projects = cursor.fetchall()
        
        projects_to_nuke = []
        for canonical, normalized in projects:
            if 'cancel' in canonical.lower() or 'cancel' in normalized.lower():
                projects_to_nuke.append((canonical, normalized))
        
        if not projects_to_nuke:
            print("No suspicious projects found in metadata.")
        else:
            print(f"Found {len(projects_to_nuke)} projects to nuke:")
            for p in projects_to_nuke:
                print(f"  - {p[0]} (table: {p[1]})")
            
            # 2. Nuke them
            for canonical, normalized in projects_to_nuke:
                print(f"\nProcessing '{canonical}'...")
                
                # Delete from metadata
                cursor.execute("DELETE FROM projects_metadata WHERE normalized_name = %s", (normalized,))
                print("  [OK] Removed from metadata")
                
                # Drop table
                cursor.execute(f'DROP TABLE IF EXISTS "{normalized}" CASCADE')
                print(f"  [OK] Dropped table '{normalized}'")
                
                # Also delete any readmes
                cursor.execute("DELETE FROM project_readmes WHERE normalized_name = %s", (normalized,))
                print("  [OK] Removed associated READMEs")

        conn.commit()
        print("\n[SUCCESS] Cleanup complete.")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Failed: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    nuke_cancelled_projects()
