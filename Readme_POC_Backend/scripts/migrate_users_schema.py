import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate_schema():
    """
    Migrate the users table to support local authentication.
    1. Add password_hash column (nullable)
    2. Make google_id nullable
    3. Make access_token nullable
    """
    db_host = os.getenv('DB_HOST', 'localhost')
    db_name = os.getenv('DB_NAME', 'projects')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    try:
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print(f"Connected to database: {db_name}")
        
        # 1. Add password_hash column
        print("Checking/Adding password_hash column...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'password_hash'
        """)
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT;")
            print("  [OK] Added password_hash column")
        else:
            print("  [SKIP] password_hash column already exists")
            
        # 2. Make google_id nullable
        print("Altering google_id to be nullable...")
        cursor.execute("ALTER TABLE users ALTER COLUMN google_id DROP NOT NULL;")
        print("  [OK] google_id is now nullable")

        # 3. Make access_token nullable
        print("Altering access_token to be nullable...")
        cursor.execute("ALTER TABLE users ALTER COLUMN access_token DROP NOT NULL;")
        print("  [OK] access_token is now nullable")
        
        print("\nMigration completed successfully.")
        
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_schema()
