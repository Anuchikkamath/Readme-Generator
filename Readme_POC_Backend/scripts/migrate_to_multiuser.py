"""
Database Migration Script for Multi-User OAuth Support
Adds users table and user_id columns to existing tables.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema_manager import SchemaManager
from app.services.storage.postgres_client import PostgresClient


def main():
    """Run database migration for multi-user support."""
    print("=" * 70)
    print("Multi-User OAuth Migration Script")
    print("=" * 70)
    print()
    print("This script will:")
    print("  1. Create the 'users' table for OAuth authentication")
    print("  2. Add 'user_id' column to 'project_readmes' table")
    print("  3. Add 'user_id' column to all project-specific tables")
    print()
    
    response = input("Do you want to proceed? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled.")
        return
    
    print()
    print("Starting migration...")
    print()
    
    schema_manager = SchemaManager()
    postgres_client = PostgresClient()
    
    # Step 1: Create users table
    print("[1/3] Creating users table...")
    if schema_manager.ensure_users_table_exists():
        print("  ✓ Users table created/verified")
    else:
        print("  ✗ Failed to create users table")
        return
    
    # Step 2: Add user_id to project_readmes table
    print("[2/3] Adding user_id to project_readmes table...")
    if schema_manager.add_user_id_column('project_readmes'):
        print("  ✓ Added user_id column to project_readmes")
    else:
        print("  ⚠ project_readmes table may not exist yet (will be created when needed)")
    
    # Step 3: Add user_id to all project tables
    print("[3/3] Adding user_id to project tables...")
    project_tables = postgres_client.list_project_tables()
    
    if not project_tables:
        print("  ⚠ No project tables found (normal for new installation)")
    else:
        for table in project_tables:
            if schema_manager.add_user_id_column(table):
                print(f"  ✓ Added user_id to {table}")
            else:
                print(f"  ⚠ Skipped {table} (may already have user_id)")
    
    print()
    print("=" * 70)
    print("Migration completed successfully!")
    print("=" * 70)
    print()
    print("Note: Existing data will have NULL user_id values.")
    print("New data will be associated with authenticated users.")
    print()


if __name__ == "__main__":
    main()
