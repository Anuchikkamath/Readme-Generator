# Multi-Project Meeting Notes Processing Pipeline

## 📋 Project Overview

This project is a **generalized, multi-project** pipeline that processes daily standup meeting notes from Gmail. The system:

1. **Fetches** emails with subject containing "Notes:" from Gmail
2. **Identifies** projects automatically from email subjects
3. **Extracts** document content from Google Docs links
4. **Processes** the unstructured notes using OpenAI's LLM to extract structured information
5. **Stores** the structured data in PostgreSQL with **one database and dynamic tables per project**

The pipeline automates the extraction and storage of meeting notes for **multiple projects**, transforming unstructured text into structured data fields that are stored in project-specific tables.

---

## 🏗️ Architecture

The project follows a modular architecture with clear separation of concerns:

```
Gmail API → Email Filtering → Project Detection → Google Docs API → LLM Processing → PostgreSQL Storage
```

### Data Flow

1. **Ingestion Layer**: Gmail API integration to fetch and filter emails
2. **Project Resolution**: Automatic project detection from email subjects
3. **Document Retrieval**: Google Docs API to extract meeting notes content
4. **LLM Processing**: OpenAI API to extract structured data from unstructured text
5. **Storage Layer**: PostgreSQL database with dynamic table creation per project

---

## 📁 Directory Structure

```
.
├── auth/                          # Google OAuth authentication
│   └── token_gen.py              # OAuth token generation and management
│
├── ingestion/                     # Email ingestion and parsing
│   ├── gmail_reader.py           # Gmail API integration
│   └── body_parser.py            # Email body parsing and doc ID extraction
│
├── documents/                     # Google Docs integration
│   └── docs_reader.py            # Fetches document content from Google Docs
│
├── llm/                           # LLM processing
│   └── ollama_client.py          # OpenAI client for structured data extraction
│
├── storage/                        # Database layer
│   ├── postgres_client.py        # PostgreSQL connection and operations
│   └── schema.sql                # Database schema reference
│
├── scripts/                        # Executable scripts
│   └── run_pipeline.py           # Main pipeline execution script
│
├── project_resolver.py            # Project name detection and normalization
├── schema_manager.py             # Dynamic schema creation and evolution
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (not in repo)
└── README.md                     # This file
```

---

## 🚀 Setup Instructions

### Prerequisites

- Python 3.8 or higher
- PostgreSQL database server
- Google Cloud Project with Gmail and Google Docs APIs enabled
- OpenAI API key

### Step 1: Clone and Navigate to Project

```bash
cd <project_directory>
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Linux/Mac
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Gmail API
   - Google Docs API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the credentials JSON file
6. Place it in the project root as `readme_credentials.json` (or update path in `auth/token_gen.py`)

### Step 5: Database Setup

**No manual database creation required!** The pipeline automatically:
- Creates the `projects` database if it doesn't exist
- Creates the `projects_metadata` table
- Creates project-specific tables dynamically

However, ensure PostgreSQL is running and accessible.

### Step 6: Environment Variables

Create a `.env` file in the project root:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_NAME=projects
DB_ADMIN_DB=postgres

# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Google OAuth (optional, defaults shown)
# GOOGLE_CREDENTIALS_FILE=readme_credentials.json
# GOOGLE_TOKEN_FILE=token.pickle
```

**Important**: Add `.env` to `.gitignore` to avoid committing sensitive information.

### Step 7: First-Time Authentication

On first run, the script will:
1. Open a browser window for Google OAuth authentication
2. Request permissions for Gmail and Google Docs access
3. Save the token to `token.pickle` for future use

---

## ⚙️ Configuration

### Database Configuration

Database credentials are configured via environment variables (see Step 6). The system uses:
- **Database name**: `projects` (configurable via `DB_NAME`)
- **Master table**: `projects_metadata` (stores project information)
- **Project tables**: Created dynamically with normalized project names

### OpenAI Configuration

Edit `llm/ollama_client.py` to change the OpenAI model:

```python
def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
    # Change model here: gpt-4, gpt-3.5-turbo, etc.
```

---

## 📦 Components Documentation

### 1. Authentication Module (`auth/token_gen.py`)

**Purpose**: Manages Google OAuth 2.0 authentication for Gmail and Google Docs APIs.

**Key Functions**:
- `get_credentials()`: Retrieves or generates OAuth credentials
  - Checks for existing `token.pickle` file
  - Refreshes expired tokens automatically
  - Initiates OAuth flow if no token exists
  - Saves token for future use

**OAuth Scopes**:
- `https://www.googleapis.com/auth/gmail.readonly` - Read Gmail messages
- `https://www.googleapis.com/auth/documents.readonly` - Read Google Docs

---

### 2. Gmail Reader (`ingestion/gmail_reader.py`)

**Purpose**: Fetches and processes emails from Gmail using the Gmail API.

**Key Functions**:
- `get_all_emails(query)`: Fetches all emails matching query with pagination
- `get_message_details(message_id)`: Fetches full message details
- `get_subject(message)`: Extracts subject line
- `is_notes_mail(message)`: Checks if email is a notes email

---

### 3. Body Parser (`ingestion/body_parser.py`)

**Purpose**: Parses email body to extract Google Docs document IDs.

**Key Functions**:
- `get_html_body(message)`: Extracts HTML body content
- `extract_notes_doc_id(message)`: Extracts Google Docs document ID from HTML

---

### 4. Documents Reader (`documents/docs_reader.py`)

**Purpose**: Fetches content from Google Docs using the Google Docs API.

**Key Functions**:
- `fetch_notes_text(doc_id)`: Fetches document title and content
  - Returns tuple: `(title, content)`

---

### 5. LLM Client (`llm/ollama_client.py`)

**Purpose**: Uses OpenAI's LLM to extract structured data from unstructured meeting notes.

**Key Functions**:
- `extract_structured_data(notes_text, meeting_date)`: Extracts structured JSON from notes

**Output Structure**:
```json
{
    "meeting_date": "YYYY-MM-DD",
    "requirements": "...",
    "tech_stack": "...",
    "discussions": "...",
    "blockers": "...",
    "conclusions": "..."
}
```

---

### 6. Project Resolver (`project_resolver.py`)

**Purpose**: Canonicalizes project names from email subjects using generic normalization and learning-based resolution.

**Key Functions**:
- `resolve_canonical_project(email_subject, llm_extracted_name)`: Resolves canonical project name
  - Extracts base string from subject
  - Removes context words (sync, discussion, internal, etc.)
  - Uses database-backed learning to maintain consistency
  - Returns (canonical_name, normalized_table_name)
- `extract_context_from_subject(subject, canonical_project)`: Extracts meeting context
- `normalize_table_name(canonical_name)`: Normalizes to valid PostgreSQL identifier

**Canonicalization Logic**:
- Removes context stopwords: sync, discussion, meeting, internal, etc.
- Splits on separators: `::`, `-`, `|`, `/`
- Examples:
  - "Notes: ACT sync" → "ACT" (table: `act`)
  - "Notes: ACT - Internal Discussion" → "ACT" (table: `act`)
  - "Notes: ACT::Sync" → "ACT" (table: `act`)
  - Context stored as `meeting_context` column

**Learning-Based Resolution**:
- Stores canonical projects in `projects_metadata` table
- Reuses existing canonical names when found
- Automatically registers new projects
- Ensures ONE table per canonical project (prevents table explosion)

---

### 7. Schema Manager (`schema_manager.py`)

**Purpose**: Manages dynamic table creation and schema evolution.

**Key Functions**:
- `ensure_database_exists()`: Creates `projects` database if needed
- `ensure_metadata_table_exists()`: Creates `projects_metadata` table
- `create_project_table(normalized_name, json_keys)`: Creates table for new project
- `alter_table_add_columns(normalized_name, new_keys)`: Adds new columns to existing table
- `register_project(project_name, normalized_name)`: Registers project in metadata

**Schema Evolution**:
- Automatically adds new columns when LLM output contains new keys
- Never drops columns automatically
- Columns are created as TEXT type for flexibility

---

### 8. PostgreSQL Client (`storage/postgres_client.py`)

**Purpose**: Manages database connections and operations for storing meeting notes.

**Key Functions**:
- `insert_meeting_note(project_name, data)`: Inserts meeting note into project table
  - Creates table if it doesn't exist
  - Adds columns if new keys are found
  - Registers project in metadata
- `get_all_projects()`: Returns list of all registered projects

---

### 9. Main Pipeline Script (`scripts/run_pipeline.py`)

**Purpose**: Orchestrates the entire pipeline from email fetching to database storage.

**Workflow**:

1. **Fetch Emails**: Gets all "Notes:" emails from Gmail
2. **Process Each Email**: For each email:
   - Extract document ID from email
   - Fetch document content from Google Docs
   - Extract structured data using LLM
   - **Resolve canonical project** from email subject (removes context words)
   - Store in canonical project's table (one table per project)
3. **Canonical Resolution**: 
   - Extracts core project name (e.g., "ACT" from "ACT sync")
   - Checks database for existing canonical project
   - Reuses existing or registers new canonical project
   - Stores context (sync, discussion, etc.) as column data

**Execution**:
```bash
python scripts/run_pipeline.py
```

---

## 🗄️ Database Schema

### Master Table: `projects_metadata`

| Column | Type | Description |
|--------|------|-------------|
| `canonical_name` | VARCHAR(255) | Canonical project name (PRIMARY KEY) |
| `normalized_name` | VARCHAR(255) | Normalized name (table name, UNIQUE) |
| `first_seen_at` | TIMESTAMP | When project was first detected |
| `last_seen_at` | TIMESTAMP | Last time project was seen |
| `example_subjects` | TEXT[] | Array of example email subjects |
| `created_at` | TIMESTAMP | Record creation timestamp |

**Purpose**: Maintains canonical project names and prevents table explosion by ensuring one table per project.

### Project Tables (Dynamic)

Each **canonical project** gets exactly ONE table. Base structure:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key (auto-generated) |
| `meeting_date` | DATE | Date of the meeting |
| `meeting_context` | TEXT | Meeting context (sync, discussion, etc.) |
| `created_at` | TIMESTAMP | Record creation timestamp |
| `{key}` | TEXT | Additional columns from LLM output |

**Examples**:
- "Notes: ACT sync" → Canonical: "ACT" → Table: `act`
- "Notes: ACT - Internal Discussion" → Canonical: "ACT" → Table: `act` (same table!)
- "Notes: ACT::Sync" → Canonical: "ACT" → Table: `act` (same table!)
- Context "sync" or "internal discussion" stored in `meeting_context` column

**Key Design**: All ACT-related emails go into ONE `act` table, regardless of subject variations.

---

## 🔧 Usage

### Running the Pipeline

Execute the main pipeline script:

```bash
python scripts/run_pipeline.py
```

### Expected Output

```
============================================================
Multi-Project Meeting Notes Processing Pipeline
============================================================

[1/6] Initializing clients...
[2/6] Fetching emails with 'Notes:' query...
✓ Fetched 25 emails

[3/6] Grouping emails by project...
✓ Found 3 projects
  - ACT: 10 email(s)
  - Project Alpha: 8 email(s)
  - Billing-System: 7 email(s)

[4/6] Processing projects...

--- Processing Project: ACT ---
  [Email 1/10] Notes: ACT March 5
    ✓ Document read: Meeting Notes (1234 characters)
    ✓ LLM extraction complete
    ✓ Stored in database

[5/6] Pipeline Summary
============================================================
Total emails fetched:        25
Projects found:             3
Total meetings stored:       23
Successfully processed:      23
Skipped/failed:             2
============================================================

[6/6] Registered Projects:
  - ACT
  - Billing-System
  - Project Alpha
```

---

## 📋 Dependencies

### Python Packages

- **google-api-python-client**: Google APIs client library
- **google-auth**: Google authentication library
- **google-auth-oauthlib**: OAuth 2.0 client for Google APIs
- **google-auth-httplib2**: HTTP transport for Google auth
- **psycopg2-binary**: PostgreSQL adapter for Python
- **openai**: OpenAI API client
- **python-dotenv**: Environment variable management

### External Services

- **Google Cloud Platform**: Gmail API and Google Docs API
- **OpenAI API**: For LLM-based data extraction
- **PostgreSQL**: Database server

---

## 🔐 Security Considerations

1. **Credentials Storage**:
   - Never commit `readme_credentials.json` to version control
   - Never commit `token.pickle` to version control
   - Never commit `.env` file to version control
   - Add these files to `.gitignore`

2. **API Keys**:
   - Store OpenAI API key in `.env` file
   - Use environment variables for sensitive data
   - Rotate keys if compromised

3. **Database Credentials**:
   - Store database credentials in `.env` file
   - Use strong passwords for production databases
   - Restrict database access to necessary IPs

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "OPENAI_API_KEY not found in environment variables"

**Solution**:
- Create a `.env` file in the project root
- Add: `OPENAI_API_KEY=your_key_here`
- Ensure `python-dotenv` is installed

#### 2. PostgreSQL Connection Errors

**Solution**:
- Verify PostgreSQL is running: `pg_isready`
- Check credentials in `.env` file
- Ensure database user has CREATE DATABASE privileges

#### 3. "No project name found in subject"

**Solution**:
- Project resolver will fall back to LLM extraction
- Emails without project names are processed separately
- Check email subject format: should contain "Notes: ProjectName ..."

#### 4. Table Creation Errors

**Solution**:
- Ensure PostgreSQL user has CREATE TABLE privileges
- Check that UUID extension is available: `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`
- Verify database name in `.env` file

---

## 🔄 Pipeline Flow Diagram

```
┌─────────────────┐
│  Gmail API      │
│  Fetch Emails   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Group by       │
│  Project        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Extract Doc ID │
│  from Email     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Google Docs    │
│  Fetch Content  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  OpenAI LLM     │
│  Extract Data   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Create/Update  │
│  Project Table  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL     │
│  Store Data     │
└─────────────────┘
```

---

## 🚧 Key Features

### Multi-Project Support

- **Automatic Project Detection**: Extracts project names from email subjects
- **Dynamic Table Creation**: Creates tables automatically for new projects
- **Schema Evolution**: Adds new columns when LLM output changes
- **Project Isolation**: Each project has its own table

### Idempotency

- Safe to run multiple times
- Duplicate detection via database constraints
- Automatic schema updates without data loss

### Flexibility

- Handles varying LLM output structures
- Dynamic column creation based on actual data
- No hardcoded project names

---

## 📝 Notes

### Project Canonicalization

- **One Table Per Canonical Project**: All variations (ACT sync, ACT discussion, etc.) → one `act` table
- **Context Extraction**: Meeting context (sync, internal, discussion) stored in `meeting_context` column
- **Learning-Based**: Project resolution improves over time as more examples are seen
- **No Hardcoding**: Generic stopword removal and separator detection, no project-specific rules

### Processing Flow

- The pipeline processes emails **sequentially**
- Each email's subject is **canonicalized** to find the core project name
- Canonical projects are **registered automatically** in `projects_metadata`
- Tables are created **on-demand** when first meeting note for a canonical project is stored
- Schema **evolves automatically** as LLM output structure changes
- **No manual database setup** required - everything is automatic

### Example Canonicalization

```
Email Subject                          → Canonical Project → Table
─────────────────────────────────────────────────────────────────
"Notes: ACT sync"                      → "ACT"            → `act`
"Notes: ACT - Internal Discussion"     → "ACT"            → `act`
"Notes: ACT::Sync"                     → "ACT"            → `act`
"Notes: PIRR Internal Standup"         → "PIRR"           → `pirr`
"Notes: PIRR meeting"                  → "PIRR"           → `pirr`
```

All ACT emails go to the same `act` table, with context stored in the `meeting_context` column.

---

## 📄 License

[Specify your license here]

---

**Last Updated**: 2024
