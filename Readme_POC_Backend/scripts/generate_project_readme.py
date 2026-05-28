"""
README Generation Script
Generates a professional README.md for a user-selected project
by aggregating all meeting data and synthesizing it via LLM.

Usage:
    python scripts/generate_project_readme.py --project act
    python scripts/generate_project_readme.py --project act --model gpt-4o
    python scripts/generate_project_readme.py --project act --no-db
    python scripts/generate_project_readme.py --list
"""

import sys
import os
import argparse

# Add parent directory and app/services path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'app', 'services'))

from storage.postgres_client import PostgresClient
from llm.readme_generator import ReadmeGenerator


def list_projects(postgres_client: PostgresClient):
    """List all available projects and their table names."""
    print("\nAvailable projects:")
    print("-" * 50)

    # From metadata
    projects = postgres_client.get_all_projects()
    if projects:
        for canonical, normalized in projects:
            # Get row count
            try:
                columns, rows = postgres_client.fetch_project_data(normalized)
                count = len(rows)
            except Exception:
                count = "?"
            print(f"  {normalized:<25} ({canonical}, {count} meetings)")
    else:
        # Fallback: list tables directly
        tables = postgres_client.list_project_tables()
        if tables:
            for table in tables:
                try:
                    columns, rows = postgres_client.fetch_project_data(table)
                    count = len(rows)
                except Exception:
                    count = "?"
                print(f"  {table:<25} ({count} meetings)")
        else:
            print("  No project tables found. Run the ingestion pipeline first:")
            print("  python scripts/run_pipeline.py")

    print()


def resolve_project(postgres_client: PostgresClient, project_arg: str):
    """
    Resolve user input to a valid (canonical_name, table_name) pair.

    Accepts:
    - Exact table name: "act"
    - Canonical name: "ACT"
    - Case-insensitive partial match

    Returns:
        tuple: (canonical_name, normalized_table_name) or (None, None)
    """
    project_lower = project_arg.lower().strip()

    # Check metadata for match
    projects = postgres_client.get_all_projects()
    for canonical, normalized in projects:
        if normalized == project_lower or canonical.lower() == project_lower:
            return canonical, normalized

    # Check if table exists directly
    if postgres_client.project_table_exists(project_lower):
        return project_arg, project_lower

    # Partial match
    for canonical, normalized in projects:
        if project_lower in normalized or project_lower in canonical.lower():
            return canonical, normalized

    return None, None


def main():
    parser = argparse.ArgumentParser(
        description="Generate a professional README.md for a project from meeting data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_project_readme.py --list
  python scripts/generate_project_readme.py --project act
  python scripts/generate_project_readme.py --project act --model gpt-4o
  python scripts/generate_project_readme.py --project act --no-db
        """
    )

    parser.add_argument(
        '--project', '-p',
        type=str,
        help='Project name (canonical or table name, e.g. "act", "hackathon")'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all available projects'
    )
    parser.add_argument(
        '--model', '-m',
        type=str,
        default='gpt-4o-mini',
        help='OpenAI model to use (default: gpt-4o-mini)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default='readmes',
        help='Output directory for README files (default: readmes/)'
    )
    parser.add_argument(
        '--no-db',
        action='store_true',
        help='Skip storing the README in the database'
    )

    args = parser.parse_args()

    # ----------------------------------------------------------------
    # Initialize
    # ----------------------------------------------------------------
    print("=" * 60)
    print("  Project README Generator")
    print("=" * 60)

    print("\n[1/5] Connecting to database...")
    try:
        postgres_client = PostgresClient()
    except Exception as e:
        print(f"[ERROR] Could not connect to database: {e}")
        sys.exit(1)

    # ----------------------------------------------------------------
    # List mode
    # ----------------------------------------------------------------
    if args.list:
        list_projects(postgres_client)
        return

    # ----------------------------------------------------------------
    # Validate project argument
    # ----------------------------------------------------------------
    if not args.project:
        print("[ERROR] --project is required. Use --list to see available projects.")
        parser.print_help()
        sys.exit(1)

    # Resolve project name
    canonical_name, table_name = resolve_project(postgres_client, args.project)
    if not table_name:
        print(f"[ERROR] Project '{args.project}' not found.")
        print("\nAvailable projects:")
        list_projects(postgres_client)
        sys.exit(1)

    print(f"  Project:  {canonical_name}")
    print(f"  Table:    {table_name}")
    print(f"  Model:    {args.model}")

    # ----------------------------------------------------------------
    # Fetch data
    # ----------------------------------------------------------------
    print(f"\n[2/5] Fetching data from '{table_name}' table...")
    try:
        columns, rows = postgres_client.fetch_project_data(table_name)
    except Exception as e:
        print(f"[ERROR] Could not fetch data: {e}")
        sys.exit(1)

    if not rows:
        print(f"[WARN] No data found in table '{table_name}'. Cannot generate README.")
        sys.exit(0)

    print(f"  Columns:  {len(columns)}")
    print(f"  Rows:     {len(rows)}")

    # Show date range
    dates = [r.get('meeting_date') for r in rows if r.get('meeting_date')]
    if dates:
        print(f"  Range:    {min(dates)} to {max(dates)}")

    # ----------------------------------------------------------------
    # Generate README via LLM
    # ----------------------------------------------------------------
    print(f"\n[3/5] Generating README...")
    try:
        generator = ReadmeGenerator(model=args.model)
        readme_content = generator.generate(
            project_name=canonical_name,
            rows=rows,
            columns=columns
        )
    except Exception as e:
        print(f"[ERROR] README generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ----------------------------------------------------------------
    # Save to disk
    # ----------------------------------------------------------------
    print(f"\n[4/5] Saving README to disk...")
    filepath = generator.save_to_disk(
        project_name=canonical_name,
        content=readme_content,
        output_dir=args.output_dir
    )
    print(f"  Saved to: {filepath}")

    # ----------------------------------------------------------------
    # Store in database (optional)
    # ----------------------------------------------------------------
    if not args.no_db:
        print(f"\n[5/5] Storing README in database...")
        try:
            postgres_client.store_readme(
                project_name=canonical_name,
                normalized_name=table_name,
                content=readme_content,
                model=args.model,
                meeting_count=len(rows)
            )
        except Exception as e:
            print(f"[WARN] Could not store in database (non-fatal): {e}")
    else:
        print(f"\n[5/5] Skipping database storage (--no-db)")

    # ----------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------
    print(f"\n{'=' * 60}")
    print(f"  README Generation Complete")
    print(f"{'=' * 60}")
    print(f"  Project:      {canonical_name}")
    print(f"  Meetings:     {len(rows)}")
    print(f"  Model:        {args.model}")
    print(f"  Output:       {filepath}")
    print(f"  Size:         {len(readme_content)} characters")
    print(f"  DB stored:    {'Yes' if not args.no_db else 'No'}")
    print()


if __name__ == "__main__":
    main()
