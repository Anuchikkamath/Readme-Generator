"""
Schema Manager Module
Manages dynamic table creation and schema evolution for project tables.
Handles migration from old schema to new canonical project schema.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2 import sql
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()


class SchemaManager:
    """Manages dynamic schema creation and evolution for project tables."""
    
    def __init__(self):
        """Initialize schema manager with database connection parameters."""
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = os.getenv('DB_PORT', '5432')
        self.user = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', '')
        self.database = os.getenv('DB_NAME', 'project')
        self.admin_db = os.getenv('DB_ADMIN_DB', 'postgres')
    
    def _get_connection(self, database_name: str = None):
        """
        Get PostgreSQL connection.
        
        Args:
            database_name: Database name (defaults to self.database)
            
        Returns:
            psycopg2.connection: Database connection
        """
        db = database_name or self.database
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=db
        )
    
    def ensure_database_exists(self):
        """Create the 'projects' database if it doesn't exist."""
        try:
            # Connect to admin database
            conn = self._get_connection(self.admin_db)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.database,)
            )
            
            exists = cursor.fetchone()
            
            if not exists:
                # Create database
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(self.database)
                    )
                )
                print(f"[OK] Created database: {self.database}")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"[ERROR] Error creating database: {e}")
            return False
    
    def ensure_metadata_table_exists(self):
        """
        Create projects_metadata table with canonical project schema.
        If old schema is detected (has 'project_name' column instead of 
        'canonical_name'), drops and recreates with new schema.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if table exists and what schema it has
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'projects_metadata'
            """)
            existing_columns = {row[0] for row in cursor.fetchall()}
            
            if existing_columns:
                if 'canonical_name' not in existing_columns:
                    # Old schema detected - drop and recreate
                    print("  > Migrating projects_metadata to new canonical schema...")
                    cursor.execute("DROP TABLE IF EXISTS projects_metadata")
                    conn.commit()
                    print("  [OK] Dropped old projects_metadata table")
                else:
                    # Correct base schema exists, but check for column updates
                    # Migration: Ensure participants column exists if table existed
                    cursor.execute("""
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'projects_metadata' AND column_name = 'participants'
                    """)
                    if not cursor.fetchone():
                        print("  > Adding participants column to projects_metadata...")
                        cursor.execute("ALTER TABLE projects_metadata ADD COLUMN participants TEXT[]")
                        conn.commit()
                    
                    cursor.close()
                    conn.close()
                    return True
            
            # Create table with new canonical schema (runs only if table didn't exist or was dropped)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects_metadata (
                    canonical_name VARCHAR(255) PRIMARY KEY,
                    normalized_name VARCHAR(255) UNIQUE NOT NULL,
                    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    example_subjects TEXT[],
                    participants TEXT[],
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            conn.commit()
            print("[OK] Created projects_metadata table (canonical schema)")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"[ERROR] Error creating metadata table: {e}")
            return False
    
    def ensure_readmes_table_exists(self):
        """
        Create project_readmes table for storing generated README documents.
        Does NOT create one table per run -- uses a single shared table.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_readmes (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    project_name VARCHAR(255) NOT NULL,
                    normalized_name VARCHAR(255) NOT NULL,
                    readme_content TEXT NOT NULL,
                    model_used VARCHAR(100),
                    meeting_count INTEGER,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Index for fast lookups by project
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_readmes_project
                ON project_readmes (normalized_name, generated_at DESC);
            """)

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            print(f"[ERROR] Error creating project_readmes table: {e}")
            return False

    def ensure_users_table_exists(self):
        """
        Create users table for multi-user OAuth authentication.
        Stores user credentials, OAuth tokens, and token expiry.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    email TEXT UNIQUE NOT NULL,
                    google_id TEXT UNIQUE NOT NULL,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT,
                    token_expiry TIMESTAMP,
                    last_synced_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Migration: add last_synced_at if users table already existed
            cursor.execute("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'last_synced_at'
            """)
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE users ADD COLUMN last_synced_at TIMESTAMP")

            # Index for fast lookups by email and google_id
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_email
                ON users (email);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_google_id
                ON users (google_id);
            """)

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            print(f"[ERROR] Error creating users table: {e}")
            return False

    def ensure_emails_table_exists(self):
        """
        Create emails table to track synced Gmail messages per user.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    gmail_message_id TEXT NOT NULL,
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    subject TEXT,
                    body TEXT,
                    date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (gmail_message_id)
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_emails_user_id
                ON emails (user_id);
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_emails_date
                ON emails (date DESC);
            """)

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            print(f"[ERROR] Error creating emails table: {e}")
            return False

    def ensure_synced_messages_table_exists(self):
        """
        Create table for tracking which Gmail message IDs were already synced
        for each user, enabling incremental sync behavior.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS synced_gmail_messages (
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    message_id TEXT NOT NULL,
                    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, message_id)
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_synced_gmail_messages_user_id
                ON synced_gmail_messages (user_id);
            """)

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            print(f"[ERROR] Error creating synced_gmail_messages table: {e}")
            return False
    
    def add_user_id_column(self, table_name: str):
        """
        Add user_id column to an existing table for multi-user support.
        
        Args:
            table_name: Table name to add user_id column to
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if column already exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name = 'user_id'
            """, (table_name,))
            
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return True  # Column already exists
            
            # Add user_id column with foreign key constraint
            cursor.execute(f"""
                ALTER TABLE {self._quote_identifier(table_name)}
                ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;
            """)
            
            # Create index for faster queries
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_user_id
                ON {self._quote_identifier(table_name)} (user_id);
            """)
            
            conn.commit()
            print(f"[OK] Added user_id column to {table_name}")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            print(f"[ERROR] Error adding user_id to {table_name}: {e}")
            return False


    def create_project_table(self, normalized_project_name: str, json_keys: List[str]):
        """
        Create a new table for a project with columns based on JSON keys.
        
        Args:
            normalized_project_name: Normalized project name (table name)
            json_keys: List of keys from LLM JSON output (will become columns)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Enable UUID extension
            cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
            
            # Start building CREATE TABLE statement
            columns = [
                "id UUID PRIMARY KEY DEFAULT uuid_generate_v4()",
                "meeting_date DATE",
                "meeting_context TEXT",
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ]
            
            # Add columns from JSON keys (sanitize column names)
            for key in json_keys:
                # Skip if already added
                if key.lower() in ['id', 'meeting_date', 'meeting_context', 'created_at']:
                    continue
                
                # Sanitize column name
                safe_key = self._sanitize_column_name(key)
                columns.append(f"{safe_key} TEXT")
            
            # Create table
            create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {self._quote_identifier(normalized_project_name)} (
                    {', '.join(columns)}
                );
            """
            
            cursor.execute(create_table_sql)
            conn.commit()
            
            print(f"[OK] Created table: {normalized_project_name}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"[ERROR] Error creating project table: {e}")
            raise
    
    def alter_table_add_columns(self, normalized_project_name: str, new_keys: List[str]):
        """
        Add new columns to an existing project table.
        Never drops columns automatically.
        
        Args:
            normalized_project_name: Normalized project name (table name)
            new_keys: List of new JSON keys to add as columns
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get existing columns
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = 'public'
            """, (normalized_project_name,))
            
            existing_columns = {row[0].lower() for row in cursor.fetchall()}
            
            # Add new columns
            for key in new_keys:
                safe_key = self._sanitize_column_name(key)
                
                # Skip if column already exists
                if safe_key.lower() in existing_columns:
                    continue
                
                # Skip reserved names
                if safe_key.lower() in ['id', 'meeting_date', 'meeting_context', 'created_at']:
                    continue
                
                # Add column
                alter_sql = f"""
                    ALTER TABLE {self._quote_identifier(normalized_project_name)}
                    ADD COLUMN IF NOT EXISTS {self._quote_identifier(safe_key)} TEXT;
                """
                
                cursor.execute(alter_sql)
                print(f"  [OK] Added column: {safe_key} to {normalized_project_name}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"[ERROR] Error altering table: {e}")
            raise
    
    def _sanitize_column_name(self, name: str) -> str:
        """
        Sanitize column name for PostgreSQL.
        
        Args:
            name: Original column name
            
        Returns:
            str: Sanitized column name
        """
        # Replace spaces and special chars with underscores
        safe = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
        # Remove multiple underscores
        safe = '_'.join(filter(None, safe.split('_')))
        # Ensure it starts with a letter
        if safe and not safe[0].isalpha():
            safe = 'col_' + safe
        # Ensure it's not empty
        if not safe:
            safe = 'col'
        # Limit length
        if len(safe) > 63:
            safe = safe[:63]
        return safe.lower()
    
    def _quote_identifier(self, name: str) -> str:
        """
        Quote PostgreSQL identifier to handle special characters.
        
        Args:
            name: Identifier name
            
        Returns:
            str: Quoted identifier
        """
        # Use double quotes for PostgreSQL identifiers
        return f'"{name}"'
    
    def get_all_table_names(self) -> List[str]:
        """
        Get all user-created table names in the database.
        
        Returns:
            list: List of table names
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return tables
            
        except Exception as e:
            print(f"[ERROR] Error listing tables: {e}")
            return []
    
    def drop_tables(self, table_names: List[str]):
        """
        Drop specified tables from the database.
        
        Args:
            table_names: List of table names to drop
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            for table_name in table_names:
                cursor.execute(
                    sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
                        sql.Identifier(table_name)
                    )
                )
                print(f"  [OK] Dropped table: {table_name}")
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"[ERROR] Error dropping tables: {e}")
            raise
