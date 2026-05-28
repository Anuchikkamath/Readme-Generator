"""
PostgreSQL Client Module
Manages database connections and operations for storing meeting notes.
Handles dynamic table creation, schema evolution, and cleanup of old tables.
"""

import psycopg2
from typing import Dict, List, Optional, Tuple
from schema_manager import SchemaManager
from app.services.project_resolver import ProjectResolver
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class PostgresClient:
    """Client for PostgreSQL database operations."""
    
    def __init__(self):
        """Initialize PostgreSQL client."""
        self.schema_manager = SchemaManager()
        
        # Ensure database exists FIRST (before anything tries to connect)
        self._ensure_database_exists()
        
        # Ensure metadata table has correct schema (migrates old schema if needed)
        self.schema_manager.ensure_metadata_table_exists()
        
        # Ensure users table exists for multi-user auth
        self.schema_manager.ensure_users_table_exists()
        
        # Ensure synced-emails tracking table exists
        self.schema_manager.ensure_emails_table_exists()

        # Ensure message-tracking table exists for incremental Gmail sync
        self.schema_manager.ensure_synced_messages_table_exists()
        
        # NOW initialize project resolver (it may query the DB)
        self.project_resolver = ProjectResolver()
    
    def get_connection(self):
        """
        Get PostgreSQL connection.
        
        Returns:
            psycopg2.connection: Database connection
        """
        return psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'projects')
        )
    
    def _ensure_database_exists(self):
        """
        Create the 'projects' database if it doesn't exist.
        Connects to admin database to create the target database.
        """
        import psycopg2.extensions
        from psycopg2 import sql
        
        db_name = os.getenv('DB_NAME', 'projects')
        admin_db = os.getenv('DB_ADMIN_DB', 'postgres')
        
        try:
            # Connect to admin database to create target database
            admin_conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', ''),
                database=admin_db
            )
            admin_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            admin_cursor = admin_conn.cursor()
            
            # Check if database exists
            admin_cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (db_name,)
            )
            
            exists = admin_cursor.fetchone()
            
            if not exists:
                # Create database
                admin_cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(db_name)
                    )
                )
                print(f"[OK] Created database: {db_name}")
            
            admin_cursor.close()
            admin_conn.close()
            
        except Exception as e:
            print(f"[WARN] Could not ensure database exists: {e}")
    
    # User Management Methods
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Get user by email address.
        
        Args:
            email: User's email address
            
        Returns:
            dict: User data or None if not found
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT id, email, google_id, access_token, refresh_token, 
                       token_expiry, created_at, password_hash, last_synced_at
                FROM users
                WHERE email = %s
                """,
                (email,)
            )
            
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if row:
                return {
                    'id': str(row[0]),
                    'email': row[1],
                    'google_id': row[2],
                    'access_token': row[3],
                    'refresh_token': row[4],
                    'token_expiry': row[5],
                    'created_at': row[6],
                    'password_hash': row[7],
                    'last_synced_at': row[8]
                }
            return None
            
        except Exception as e:
            print(f"[ERROR] Error fetching user by email: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """
        Get user by ID.
        
        Args:
            user_id: User's UUID
            
        Returns:
            dict: User data or None if not found
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT id, email, google_id, access_token, refresh_token, 
                       token_expiry, created_at, password_hash, last_synced_at
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )
            
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if row:
                return {
                    'id': str(row[0]),
                    'email': row[1],
                    'google_id': row[2],
                    'access_token': row[3],
                    'refresh_token': row[4],
                    'token_expiry': row[5],
                    'created_at': row[6],
                    'password_hash': row[7],
                    'last_synced_at': row[8]
                }
            return None
            
        except Exception as e:
            print(f"[ERROR] Error fetching user by ID: {e}")
            return None
    
    def create_or_update_user(self, email: str, google_id: Optional[str] = None, 
                              access_token: Optional[str] = None, 
                              refresh_token: Optional[str] = None,
                              token_expiry = None,
                              password_hash: Optional[str] = None) -> Optional[Dict]:
        """
        Create a new user or update existing user's tokens/password.
        Handles both Google OAuth and Local Auth users.
        
        Args:
            email: User's email
            google_id: Google user ID (optional for local users)
            access_token: OAuth access token (optional)
            refresh_token: OAuth refresh token (optional)
            token_expiry: Token expiration timestamp (optional)
            password_hash: Hashed password (optional for Google users)
            
        Returns:
            dict: Created/updated user data
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Use ON CONFLICT to handle upserts
            # Note: We need to be careful not to overwrite Google creds with nulls if logging in locally later?
            # actually, local register -> sets password. google login -> sets google_id.
            # safe to coalesce?
            
            cursor.execute(
                """
                INSERT INTO users (email, google_id, access_token, refresh_token, token_expiry, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (email)
                DO UPDATE SET
                    google_id = COALESCE(EXCLUDED.google_id, users.google_id),
                    access_token = COALESCE(EXCLUDED.access_token, users.access_token),
                    refresh_token = COALESCE(EXCLUDED.refresh_token, users.refresh_token),
                    token_expiry = COALESCE(EXCLUDED.token_expiry, users.token_expiry),
                    password_hash = COALESCE(EXCLUDED.password_hash, users.password_hash)
                RETURNING id, email, google_id, access_token, refresh_token, 
                          token_expiry, created_at, password_hash
                """,
                (email, google_id, access_token, refresh_token, token_expiry, password_hash)
            )
            
            row = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()
            
            if row:
                return {
                    'id': str(row[0]),
                    'email': row[1],
                    'google_id': row[2],
                    'access_token': row[3],
                    'refresh_token': row[4],
                    'token_expiry': row[5],
                    'created_at': row[6],
                    'has_password': bool(row[7])
                }
            return None
            
        except Exception as e:
            print(f"[ERROR] Error creating/updating user: {e}")
            return None
    
    def update_access_token(self, user_id: str, access_token: str, token_expiry):
        """
        Update user's access token after refresh.
        
        Args:
            user_id: User's UUID
            access_token: New access token
            token_expiry: New token expiration timestamp
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                """
                UPDATE users
                SET access_token = %s, token_expiry = %s
                WHERE id = %s
                """,
                (access_token, token_expiry, user_id)
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"[ERROR] Error updating access token: {e}")
            raise

    def get_synced_message_ids(self, user_id: str, message_ids: List[str]) -> set:
        """
        Get subset of message IDs that are already synced for this user.

        Args:
            user_id: User UUID
            message_ids: Candidate Gmail message IDs

        Returns:
            set: Message IDs already present in synced_gmail_messages
        """
        if not user_id or not message_ids:
            return set()

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT message_id
                FROM synced_gmail_messages
                WHERE user_id = %s
                  AND message_id = ANY(%s)
                """,
                (user_id, message_ids)
            )

            result = {row[0] for row in cursor.fetchall()}
            cursor.close()
            conn.close()
            return result
        except Exception as e:
            print(f"[WARN] Error fetching synced message IDs: {e}")
            return set()

    def get_user_last_synced_at(self, user_id: str):
        """
        Get the user's last successful Gmail sync timestamp.
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT last_synced_at FROM users WHERE id = %s",
                (user_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row[0] if row else None
        except Exception as e:
            print(f"[WARN] Error fetching last_synced_at: {e}")
            return None

    def update_user_last_synced_at(self, user_id: str, synced_at: datetime):
        """
        Update user's last synced timestamp.
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE users
                SET last_synced_at = %s
                WHERE id = %s
                """,
                (synced_at, user_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"[WARN] Error updating last_synced_at: {e}")

    def insert_email_if_new(self, user_id: str, gmail_message_id: str,
                            subject: str, body: str, email_date):
        """
        Insert Gmail email into emails table if not already stored.

        Returns:
            bool: True if inserted, False if duplicate/no-op
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO emails (gmail_message_id, user_id, subject, body, date)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (gmail_message_id) DO NOTHING
                RETURNING id
                """,
                (gmail_message_id, user_id, subject, body, email_date)
            )
            inserted = cursor.fetchone() is not None
            conn.commit()
            cursor.close()
            conn.close()
            return inserted
        except Exception as e:
            print(f"[WARN] Error inserting email record: {e}")
            return False

    def mark_message_as_synced(self, user_id: str, message_id: str):
        """
        Mark a Gmail message as synced for a user.

        Args:
            user_id: User UUID
            message_id: Gmail message ID
        """
        if not user_id or not message_id:
            return

        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO synced_gmail_messages (user_id, message_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, message_id) DO NOTHING
                """,
                (user_id, message_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"[WARN] Error marking message as synced: {e}")

    
    def insert_meeting_note(self, email_subject: str, data: dict, 
                           llm_extracted_project: Optional[str] = None,
                           user_id: Optional[str] = None,
                           participants: Optional[List[str]] = None):
        """
        Insert structured meeting note data into the canonical project's table.
        Uses learning-based project resolution to ensure one table per project.
        
        Args:
            email_subject: Email subject line (for project resolution)
            data: Dictionary with meeting note data (from LLM JSON)
            llm_extracted_project: Optional project name from LLM extraction
            user_id: User UUID for multi-user data isolation
            participants: List of email addresses from the meeting
        """
        # Resolve canonical project using learning-based approach
        canonical_name, normalized_name = self.project_resolver.resolve_canonical_project(
            email_subject, llm_extracted_project, participants
        )
        
        # Update project participants in metadata
        if participants:
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE projects_metadata 
                    SET participants = (
                        SELECT array_agg(DISTINCT p) 
                        FROM unnest(
                            array_cat(
                                COALESCE(participants, ARRAY[]::TEXT[]),
                                %s::TEXT[]
                            )
                        ) AS p
                    )
                    WHERE canonical_name = %s
                """, (participants, canonical_name))
                conn.commit()
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"[WARN] Could not update project participants: {e}")
        
        # Extract context from subject
        context = self.project_resolver.extract_context_from_subject(
            email_subject, canonical_name
        )
        
        # Add context to data if found
        if context:
            data['meeting_context'] = context
        
        # Get all keys from data (excluding reserved keys)
        json_keys = [k for k in data.keys() 
                     if k.lower() not in ['id', 'created_at', 'project_name', 'canonical_name']]
        
        # Ensure table exists and has all needed columns
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = 'public'
            """, (normalized_name,))
            
            existing_columns = {row[0].lower() for row in cursor.fetchall()}
            cursor.close()
            conn.close()
            
            if not existing_columns:
                # Table doesn't exist - create it
                self.schema_manager.create_project_table(normalized_name, json_keys)
            else:
                # Table exists - check for new columns
                existing_keys = {col.lower() for col in existing_columns}
                new_keys = [k for k in json_keys 
                          if self.schema_manager._sanitize_column_name(k).lower() not in existing_keys]
                
                if new_keys:
                    self.schema_manager.alter_table_add_columns(normalized_name, new_keys)
        
        except psycopg2.errors.UndefinedTable:
            self.schema_manager.create_project_table(normalized_name, json_keys)
        
        # Ensure user_id column exists in table (for multi-user support)
        if user_id:
            self.schema_manager.add_user_id_column(normalized_name)
        
        # Insert data
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Prepare columns and values
            columns = []
            values = []
            placeholders = []
            
            # Handle meeting_date - convert None/"None" to NULL
            meeting_date = data.get('meeting_date')
            if meeting_date is None or str(meeting_date).strip().lower() in ['none', '']:
                meeting_date = None
            else:
                meeting_date_str = str(meeting_date).strip()
                if meeting_date_str and meeting_date_str.lower() != 'none':
                    meeting_date = meeting_date_str
                else:
                    meeting_date = None
            
            columns.append('meeting_date')
            values.append(meeting_date)
            placeholders.append('%s')
            
            # Add other columns from data
            for key, value in data.items():
                if key.lower() in ['id', 'meeting_date', 'created_at', 'project_name', 'canonical_name']:
                    continue
                
                safe_key = self.schema_manager._sanitize_column_name(key)
                columns.append(safe_key)
                
                # Handle None values properly
                if value is None or str(value).strip().lower() in ['none', '']:
                    processed_value = None
                elif isinstance(value, (dict, list)):
                    import json
                    processed_value = json.dumps(value)
                else:
                    processed_value = str(value)
                
                values.append(processed_value)
                placeholders.append('%s')
            
            # Add user_id if provided
            if user_id:
                columns.append('user_id')
                values.append(user_id)
                placeholders.append('%s')
            
            # Build INSERT statement
            columns_str = ', '.join([f'"{col}"' for col in columns])
            placeholders_str = ', '.join(placeholders)
            
            insert_sql = f"""
                INSERT INTO "{normalized_name}" ({columns_str}, created_at)
                VALUES ({placeholders_str}, CURRENT_TIMESTAMP)
                ON CONFLICT DO NOTHING;
            """
            
            cursor.execute(insert_sql, values)
            conn.commit()
            
            print(f"[OK] Stored meeting note in table: {normalized_name}")
            
        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Error inserting data: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_all_projects(self) -> List[str]:
        """
        Get list of all registered canonical projects.
        
        Returns:
            list: List of canonical project names
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT canonical_name, normalized_name 
                FROM projects_metadata 
                ORDER BY canonical_name
            """)
            projects = cursor.fetchall()
            cursor.close()
            conn.close()
            return projects
        except Exception as e:
            print(f"[WARN] Could not fetch projects: {e}")
            return []
    
    def get_projects_for_user(self, user_id: str) -> List[Tuple[str, str]]:
        """
        Get list of projects that contain data for the specific user.
        Iterates through known projects and checks for user's data presence.
        
        Args:
            user_id: User UUID
            
        Returns:
            list: List of (canonical_name, normalized_name) tuples
        """
        try:
            # 1. Get all known projects
            all_projects = self.get_all_projects()
            user_projects = []
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            for canonical, normalized in all_projects:
                try:
                    # Check if user_id column exists
                    cursor.execute("""
                        SELECT 1 
                        FROM information_schema.columns 
                        WHERE table_name = %s AND column_name = 'user_id'
                    """, (normalized,))
                    
                    if not cursor.fetchone():
                        continue
                        
                    # Check if user has data in this table
                    cursor.execute(
                        f'SELECT 1 FROM "{normalized}" WHERE user_id = %s LIMIT 1',
                        (user_id,)
                    )
                    
                    if cursor.fetchone():
                        user_projects.append((canonical, normalized))
                        
                except Exception as e:
                    # Skip problematic tables but continue
                    print(f"[WARN] Error checking project '{normalized}' for user: {e}")
                    conn.rollback() # Reset transaction state
            
            cursor.close()
            conn.close()
            return user_projects
            
        except Exception as e:
            print(f"[ERROR] Error fetching user projects: {e}")
            return []

    def fetch_project_data(self, table_name: str, user_id: Optional[str] = None) -> Tuple:
        """
        Fetch all rows from a project table, ordered chronologically.
        Optionally filtered by user_id.

        Args:
            table_name: Normalized table name
            user_id: Optional User UUID to filter by

        Returns:
            tuple: (columns: List[str], rows: List[Dict])
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Get column names
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """, (table_name,))
            columns = [row[0] for row in cursor.fetchall()]

            if not columns:
                raise ValueError(f"Table '{table_name}' does not exist or has no columns.")

            # Build query
            query = f'SELECT * FROM "{table_name}"'
            params = []
            
            if user_id:
                # Check if user_id column exists to avoid error on legacy tables
                if 'user_id' in columns:
                    query += ' WHERE user_id = %s'
                    params.append(user_id)
                else:
                    # If table has no user_id column, return nothing for safety in multi-user mode
                    # OR return everything if it's a legacy public mode? 
                    # STRICT MODE: Return nothing implies "this isn't yours"
                    # But for migration/mixed data, maybe we want to see it?
                    # User asked: "show the projects which are fetched from that mail id"
                    # So strict filtering is better.
                    return columns, []

            query += ' ORDER BY meeting_date ASC NULLS LAST, created_at ASC'
            
            # Fetch all rows
            cursor.execute(query, tuple(params))
            raw_rows = cursor.fetchall()

            # Convert to list of dicts
            rows = []
            for raw in raw_rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    val = raw[i]
                    # Convert date/datetime to string for serialization
                    if hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    row_dict[col] = val
                rows.append(row_dict)

            return columns, rows

        finally:
            cursor.close()
            conn.close()

    def project_table_exists(self, table_name: str) -> bool:
        """
        Check if a project table exists in the database.

        Args:
            table_name: Normalized table name

        Returns:
            bool: True if table exists
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT 1 FROM information_schema.tables
                WHERE table_name = %s AND table_schema = 'public'
            """, (table_name,))
            return cursor.fetchone() is not None
        finally:
            cursor.close()
            conn.close()

    def store_readme(self, project_name: str, normalized_name: str,
                     content: str, model: str, meeting_count: int) -> Optional[str]:
        """
        Store a generated README in the project_readmes table.

        Args:
            project_name: Canonical project name
            normalized_name: Normalized table name
            content: README markdown content
            model: LLM model used for generation
            meeting_count: Number of meetings used
            
        Returns:
            str: UUID of the stored README, or None if failed
        """
        # Ensure the readmes table exists
        self.schema_manager.ensure_readmes_table_exists()

        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO project_readmes
                    (project_name, normalized_name, readme_content,
                     model_used, meeting_count)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (project_name, normalized_name, content, model, meeting_count))

            row = cursor.fetchone()
            readme_id = str(row[0]) if row else None
            
            conn.commit()
            print(f"[OK] README stored in database (id: {readme_id})")
            return readme_id

        except Exception as e:
            conn.rollback()
            print(f"[ERROR] Failed to store README in database: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def list_project_tables(self) -> List[str]:
        """
        List all project tables (excluding metadata/system tables).

        Returns:
            list: List of table names
        """
        all_tables = self.schema_manager.get_all_table_names()
        system_tables = {'projects_metadata', 'project_readmes'}
        return [t for t in all_tables if t not in system_tables]

    def cleanup_old_tables(self, dry_run: bool = True) -> List[str]:
        """
        Find and optionally drop old fragmented tables that should have been
        consolidated into canonical project tables.
        
        For example, if canonical project "ACT" exists with table "act",
        old tables like "act_sync", "act_internal_discussion" are orphaned.
        
        Args:
            dry_run: If True, only list tables to drop. If False, actually drop them.
            
        Returns:
            list: List of orphaned table names
        """
        try:
            # Get all tables
            all_tables = self.schema_manager.get_all_table_names()
            
            # Get canonical project tables
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT normalized_name FROM projects_metadata")
            canonical_tables = {row[0] for row in cursor.fetchall()}
            cursor.close()
            conn.close()
            
            # Find orphaned tables (tables that are prefixed by a canonical table name)
            orphaned = []
            for table in all_tables:
                if table == 'projects_metadata':
                    continue
                
                # Check if this table is a canonical table
                if table in canonical_tables:
                    continue
                
                # Check if this table is an orphaned variant of a canonical table
                for canonical in canonical_tables:
                    if table.startswith(canonical + '_') and table != canonical:
                        orphaned.append(table)
                        break
            
            if orphaned:
                print(f"\nFound {len(orphaned)} orphaned table(s) from old fragmented resolution:")
                for table in orphaned:
                    print(f"  - {table}")
                
                if not dry_run:
                    print("\nDropping orphaned tables...")
                    self.schema_manager.drop_tables(orphaned)
                    print("[OK] Cleanup complete")
                else:
                    print("\n  Run with dry_run=False to drop these tables")
                    print("  Or run: python scripts/cleanup_old_tables.py")
            else:
                print("[OK] No orphaned tables found")
            
            return orphaned
            
        except Exception as e:
            print(f"[WARN] Error during cleanup: {e}")
            return []
