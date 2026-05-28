"""
Cleanup Script: Drop old fragmented tables
Removes orphaned tables created by the old (broken) project resolution
that created separate tables for each subject variation.

Usage:
    python scripts/cleanup_old_tables.py              # Dry run (list only)
    python scripts/cleanup_old_tables.py --drop        # Drop orphaned tables only
    python scripts/cleanup_old_tables.py --drop-all    # Drop ALL project tables (fresh start)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schema_manager import SchemaManager


def main():
    drop = '--drop' in sys.argv
    drop_all = '--drop-all' in sys.argv

    print("=" * 60)
    print("  Old Table Cleanup Script")
    print("=" * 60)

    if drop_all:
        print("\n  MODE: DROP ALL (will drop ALL project tables for fresh start!)")
    elif drop:
        print("\n  MODE: DROP (will drop orphaned tables only)")
    else:
        print("\n  MODE: DRY RUN (listing only)")
        print("  Use --drop-all to drop ALL old tables for a fresh start")

    print()

    schema_manager = SchemaManager()
    schema_manager.ensure_database_exists()
    schema_manager.ensure_metadata_table_exists()

    # Show all tables
    all_tables = schema_manager.get_all_table_names()
    project_tables = [t for t in all_tables if t != 'projects_metadata']

    print(f"\nAll tables in database ({len(all_tables)}):")
    for t in all_tables:
        marker = " (metadata)" if t == 'projects_metadata' else ""
        print(f"  - {t}{marker}")

    if drop_all:
        if project_tables:
            print(f"\nDropping ALL {len(project_tables)} project tables...")
            schema_manager.drop_tables(project_tables)

            # Also clear metadata
            try:
                conn = schema_manager._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM projects_metadata")
                conn.commit()
                cursor.close()
                conn.close()
                print("[OK] Cleared projects_metadata")
            except Exception as e:
                print(f"[WARN] Could not clear metadata: {e}")

            print("\n[OK] All project tables dropped. Run the pipeline to recreate:")
            print("  python scripts/run_pipeline.py")
        else:
            print("\nNo project tables to drop.")
    elif drop:
        # Only drop orphaned tables (tables not in metadata)
        try:
            conn = schema_manager._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT normalized_name FROM projects_metadata")
            canonical_tables = {row[0] for row in cursor.fetchall()}
            cursor.close()
            conn.close()
        except Exception:
            canonical_tables = set()

        orphaned = [t for t in project_tables if t not in canonical_tables]

        if orphaned:
            print(f"\nDropping {len(orphaned)} orphaned tables...")
            schema_manager.drop_tables(orphaned)
            print("[OK] Cleanup complete")
        else:
            print("\nNo orphaned tables to drop.")
    else:
        print(f"\n{len(project_tables)} project table(s) exist.")
        if project_tables:
            print("\nTo drop ALL old tables and start fresh:")
            print("  python scripts/cleanup_old_tables.py --drop-all")

    print("\nDone.")


if __name__ == '__main__':
    main()
