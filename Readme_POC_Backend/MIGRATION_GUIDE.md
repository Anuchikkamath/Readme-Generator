# PostgreSQL Migration Guide

This project has been migrated from SQLite to PostgreSQL with **one database per project** (matching the original SQLite behavior).

## Changes Overview

### Database Structure
- **Before**: Multiple SQLite database files (one per project) in `databases/` directory
- **After**: Multiple PostgreSQL databases (one per project) on PostgreSQL server
- **Behavior**: Each project gets its own isolated PostgreSQL database, just like the old SQLite approach

### Schema (Per Project Database)
Each project database contains the same schema with 4 main tables:

1. **projects** - Stores project information
   - UUID primary key
   - Unique project names
   - Timestamps (created_at, updated_at)
   - Note: Each database typically has one project record

2. **transcripts** - Stores meeting transcripts/notes
   - UUID primary key
   - Foreign key to projects
   - `raw_transcript` (JSONB) - Full transcript data
   - `extracted_data` (JSONB) - Structured data from LLM extraction
   - Source URL for tracking

3. **transcript_insights** - Stores insights derived from transcripts
   - UUID primary key
   - Foreign key to transcripts
   - JSONB for flexible insight data storage

4. **readme_outputs** - Stores generated README files
   - UUID primary key
   - Foreign key to projects
   - Content and file paths

### Database Naming
- Project names are sanitized to valid PostgreSQL database names
- Special characters are replaced with underscores
- Example: "My Project" → database name: `my_project`
- Example: "GSE-COM Demo" → database name: `gse_com_demo`

## Setup Instructions

### 1. Install PostgreSQL

Make sure PostgreSQL is installed and running on your system.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `psycopg2-binary` - PostgreSQL adapter
- `sqlalchemy` - ORM for database operations
- `python-dotenv` - Environment variable management

### 3. Configure Environment Variables

Copy `env.example.txt` to `.env` and update with your PostgreSQL credentials:

```bash
cp env.example.txt .env
```

Edit `.env`:
```
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_ADMIN_DB=postgres
```

**Note**: `DB_NAME` is no longer used since each project has its own database.

### 4. Initialize a Project Database (Optional)

You can pre-initialize a project database:

```bash
python db_init.py --project "My Project Name"
```

**Note**: Databases are created automatically when you first insert data for a project, so this step is optional.

### 5. Verify Installation

Run the example usage script to test the setup:

```bash
python example_usage.py
```

## API Compatibility

The `DatabaseManager` class maintains backward compatibility with the existing API:

- `insert_meeting(project_name, meeting_data, source_url=None)` - Works as before, creates database automatically
- `get_all_meetings(project_name)` - Returns list of meeting dictionaries
- `get_meeting_by_date(project_name, date)` - Finds meetings by date
- `list_projects()` - Lists all project names (by querying all databases)
- `project_exists(project_name)` - Checks if project database exists

## Key Differences from Single-Database Approach

### One Database Per Project
- Each project has complete isolation
- Easier to backup/restore individual projects
- Matches original SQLite behavior
- Project names are sanitized to database names

### Automatic Database Creation
- Databases are created automatically on first use
- No need to manually create databases for each project
- Schema is created automatically when needed

### Database Listing
- `list_projects()` queries all databases to find projects
- Each database is queried for its project name

## New Features

### Additional Methods

- `get_project_by_name(project_name)` - Get Project object from project's database
- `create_transcript_insight(transcript_id, insight_type, insight_data, project_name)` - Store insights
- `save_readme_output(project_name, readme_type, content, file_path)` - Store README outputs

### JSONB Benefits

- Efficient JSON queries using PostgreSQL's JSONB operators
- Indexed JSON fields for fast searches
- Flexible schema for varying meeting data structures

## Migration from SQLite Data

If you have existing SQLite databases, you'll need to write a migration script to:

1. Read data from each SQLite database file
2. Extract project name from filename
3. Create PostgreSQL database for that project
4. Insert data into PostgreSQL using `DatabaseManager.insert_meeting()`

Example migration approach:
```python
from database import DatabaseManager
import sqlite3
import os

db_manager = DatabaseManager()

# For each SQLite database file
for db_file in os.listdir('databases'):
    if db_file.endswith('.db'):
        # Extract project name from filename
        project_name = db_file[:-3].replace('_', ' ')
        
        # Connect to SQLite
        conn = sqlite3.connect(f'databases/{db_file}')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM meetings")
        rows = cursor.fetchall()
        
        # Get column names
        columns = [desc[0] for desc in cursor.description]
        
        # Insert each meeting into PostgreSQL
        for row in rows:
            meeting_data = dict(zip(columns, row))
            meeting_data.pop('id', None)  # Remove SQLite id
            db_manager.insert_meeting(project_name, meeting_data)
        
        conn.close()
```

## Troubleshooting

### Connection Errors

- Verify PostgreSQL is running: `pg_isready` or `psql -U postgres`
- Check credentials in `.env` file
- Ensure database user has CREATE DATABASE privileges

### Import Errors

- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Verify virtual environment is activated

### UUID Extension

The initialization script automatically enables the `uuid-ossp` extension. If you see errors:
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### Database Name Issues

- Project names are automatically sanitized
- Invalid characters are replaced with underscores
- Database names are limited to 63 characters (PostgreSQL limit)
- If a project name results in an invalid database name, it will be prefixed with `p_`

## Performance Considerations

- GIN indexes on JSONB columns enable fast JSON queries
- Foreign key indexes improve join performance
- Timestamp indexes help with date-based queries
- Each project database is independent, so queries are isolated

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | (empty) | Database password |
| `DB_ADMIN_DB` | `postgres` | Admin database for creating new DBs |

**Note**: `DB_NAME` is no longer used. Each project has its own database.

## Example Workflow

```python
from database import DatabaseManager

db_manager = DatabaseManager()

# Insert a meeting - database is created automatically
db_manager.insert_meeting(
    project_name="My Project",
    meeting_data={
        "date": "2024-01-15",
        "requirements": "Key requirements",
        "tech_stack": "Python, PostgreSQL"
    }
)

# Query meetings
meetings = db_manager.get_all_meetings("My Project")

# List all projects
projects = db_manager.list_projects()
```
