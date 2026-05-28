# Transcripts POC - HFN Daily Standup Notes Processing Pipeline

## 📋 Project Overview

This project is a Proof of Concept (POC) for an automated pipeline that processes daily standup meeting notes from Gmail. The system:

1. **Fetches** emails with subject "HFN Daily Standup" from Gmail
2. **Identifies** "Notes" emails containing Google Docs links
3. **Extracts** the document content from Google Docs
4. **Processes** the unstructured notes using OpenAI's LLM to extract structured information
5. **Stores** the structured data in a PostgreSQL database

The pipeline automates the extraction and storage of meeting notes, transforming unstructured text into structured data fields: requirements, tech stack, discussions, blockers, and conclusions.

---

## 🏗️ Architecture

The project follows a modular architecture with clear separation of concerns:

```
Gmail API → Email Filtering → Google Docs API → LLM Processing → PostgreSQL Storage
```

### Data Flow

1. **Ingestion Layer**: Gmail API integration to fetch and filter emails
2. **Document Retrieval**: Google Docs API to extract meeting notes content
3. **LLM Processing**: OpenAI API to extract structured data from unstructured text
4. **Storage Layer**: PostgreSQL database to persist structured meeting notes

---

## 📁 Directory Structure

```
Transcripts_POC/
├── auth/                          # Google OAuth authentication
│   ├── token_gen.py              # OAuth token generation and management
│   └── raj_anna_credentials.json # Google OAuth credentials (not in repo)
│
├── config/                        # Configuration files
│   └── settings.py               # Application settings (currently empty)
│
├── documents/                     # Google Docs integration
│   └── docs_reader.py            # Fetches document content from Google Docs
│
├── ingestion/                     # Email ingestion and parsing
│   ├── gmail_reader.py           # Gmail API integration
│   └── body_parser.py            # Email body parsing and doc ID extraction
│
├── llm/                           # LLM processing
│   ├── ollama_client.py          # OpenAI client for structured data extraction
│   └── prompts/                  # LLM prompt templates (directory)
│
├── scripts/                       # Executable scripts
│   ├── run_hfn_pipeline.py       # Main pipeline execution script
│   └── test_docs_reader.py       # Testing script for docs reader
│
├── storage/                       # Database layer
│   ├── postgres_client.py        # PostgreSQL connection and operations
│   └── schema.sql                # Database schema definition
│
├── requirements.txt              # Python dependencies
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
cd Transcripts_POC
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
pip install openai python-dotenv  # Additional packages for OpenAI integration
```

**Note**: The `requirements.txt` currently lists `ollama`, but the project now uses OpenAI. You may want to update it to include:
- `openai`
- `python-dotenv`

### Step 4: Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Gmail API
   - Google Docs API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the credentials JSON file
6. Place it in the `auth/` directory as `raj_anna_credentials.json` (or update the path in `auth/token_gen.py`)

### Step 5: Database Setup

1. Create a PostgreSQL database:

```sql
CREATE DATABASE hfn_notes;
```

2. Run the schema script:

```bash
psql -U postgres -d hfn_notes -f storage/schema.sql
```

Or manually execute the SQL in `storage/schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS hfn_daily_standup_notes (
    id SERIAL PRIMARY KEY,
    meeting_date DATE,
    requirements TEXT,
    tech_stack TEXT,
    discussions TEXT,
    blockers TEXT,
    conclusions TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (meeting_date)
);
```

3. Update database credentials in `storage/postgres_client.py`:
   - `host`: Database host (default: "localhost")
   - `database`: Database name (default: "hfn_notes")
   - `user`: PostgreSQL username (default: "postgres")
   - `password`: PostgreSQL password (default: "root")
   - `port`: Database port (default: 5432)

### Step 6: Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
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

Edit `storage/postgres_client.py` to match your PostgreSQL setup:

```python
def get_connection():
    return psycopg2.connect(
        host="localhost",      # Your PostgreSQL host
        database="hfn_notes",  # Your database name
        user="postgres",        # Your PostgreSQL username
        password="root",        # Your PostgreSQL password
        port=5432              # Your PostgreSQL port
    )
```

### OpenAI Configuration

Edit `llm/ollama_client.py` to change the OpenAI model:

```python
MODEL = "gpt-4o-mini"  # Change to: gpt-4, gpt-3.5-turbo, etc.
```

### Google OAuth Credentials Path

If your credentials file is in a different location, update `auth/token_gen.py`:

```python
flow = InstalledAppFlow.from_client_secrets_file(
    "auth\\raj_anna_credentials.json",  # Update this path
    SCOPES
)
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

**Files Generated**:
- `token.pickle`: Stores OAuth token for reuse (auto-generated)

---

### 2. Gmail Reader (`ingestion/gmail_reader.py`)

**Purpose**: Fetches and processes emails from Gmail using the Gmail API.

**Key Functions**:

- `get_all_hfn_daily_standup_mails()`: 
  - Searches for all emails with subject "HFN Daily Standup"
  - Handles pagination automatically
  - Returns list of message metadata

- `get_message_details(message_id)`:
  - Fetches full message details including body and headers
  - Returns complete message object

- `get_subject(message)`:
  - Extracts subject line from message headers
  - Returns empty string if not found

- `is_notes_mail(message)`:
  - Checks if email subject starts with "Notes:"
  - Used to filter only notes emails

**Dependencies**: Google Gmail API v1

---

### 3. Body Parser (`ingestion/body_parser.py`)

**Purpose**: Parses email body to extract Google Docs document IDs.

**Key Functions**:

- `get_html_body(message)`:
  - Recursively walks through email MIME parts
  - Extracts HTML body content
  - Handles nested MIME structures

- `extract_notes_doc_id(message)`:
  - Parses HTML body for Google Docs URLs
  - Uses regex pattern: `https://docs.google.com/document/d/([a-zA-Z0-9_-]+)`
  - Returns the first document ID found
  - Returns `None` if no document ID is found

**Regex Pattern**: `r'https://docs.google.com/document/d/([a-zA-Z0-9_-]+)'`

---

### 4. Documents Reader (`documents/docs_reader.py`)

**Purpose**: Fetches content from Google Docs using the Google Docs API.

**Key Functions**:

- `fetch_notes_text(doc_id: str) -> tuple[str, str]`:
  - Takes a Google Docs document ID
  - Fetches document structure via Google Docs API
  - Extracts title and plain text content
  - Returns tuple: `(title, content)`
  - Handles document structure parsing

**Dependencies**: Google Docs API v1

**Return Format**: `(document_title, document_content)`

---

### 5. LLM Client (`llm/ollama_client.py`)

**Purpose**: Uses OpenAI's LLM to extract structured data from unstructured meeting notes.

**Key Functions**:

- `extract_structured_data(notes_text: str, meeting_date: str) -> dict`:
  - Takes raw meeting notes text and meeting date
  - Constructs prompt for OpenAI API
  - Sends request to OpenAI chat completions API
  - Extracts JSON from LLM response using multiple strategies
  - Returns structured dictionary

**LLM Configuration**:
- Model: `gpt-4o-mini` (configurable)
- Temperature: `0.3` (for consistent output)
- Timeout: `120` seconds

**JSON Extraction Strategies**:
1. **Markdown Code Blocks**: Extracts JSON from ````json ... ```` blocks
2. **Balanced Braces**: Finds JSON object by counting opening/closing braces
3. **Regex Fallback**: Uses regex pattern as last resort

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

**Error Handling**:
- Raises `ValueError` if no valid JSON found
- Raises `ValueError` if JSON parsing fails
- Provides detailed error messages with LLM output snippet

**Environment Variables**:
- `OPENAI_API_KEY`: Required OpenAI API key (loaded from `.env`)

---

### 6. PostgreSQL Client (`storage/postgres_client.py`)

**Purpose**: Manages database connections and operations for storing meeting notes.

**Key Functions**:

- `get_connection()`:
  - Creates PostgreSQL connection using psycopg2
  - Returns connection object
  - Configured for localhost PostgreSQL instance

- `insert_meeting_note(data: dict)`:
  - Inserts structured meeting note data into database
  - Uses `ON CONFLICT DO NOTHING` to prevent duplicates
  - Expects dictionary with keys:
    - `meeting_date`: Date string (YYYY-MM-DD)
    - `requirements`: Text field
    - `tech_stack`: Text field
    - `discussions`: Text field
    - `blockers`: Text field
    - `conclusions`: Text field
  - Commits transaction and closes connection

**Database Table**: `hfn_daily_standup_notes`

**Conflict Handling**: Uses `UNIQUE (meeting_date)` constraint to prevent duplicate entries for the same date.

---

### 7. Main Pipeline Script (`scripts/run_hfn_pipeline.py`)

**Purpose**: Orchestrates the entire pipeline from email fetching to database storage.

**Workflow**:

1. **Fetch Emails**: Gets all "HFN Daily Standup" emails from Gmail
2. **Get Details**: Fetches full message details for each email
3. **Sort Chronologically**: Sorts messages by internal date (oldest first)
4. **Filter Notes**: Only processes emails with subject starting with "Notes:"
5. **Extract Document ID**: Parses email body to find Google Docs link
6. **Fetch Document**: Retrieves document title and content
7. **Extract Date**: Derives meeting date from email timestamp
8. **LLM Processing**: Sends notes to OpenAI for structured extraction
9. **Data Validation**: Ensures all required fields are present
10. **Date Validation**: Validates and corrects meeting_date format
11. **Database Storage**: Inserts structured data into PostgreSQL

**Error Handling**:
- Skips emails without document IDs
- Catches `ValueError` and `KeyError` during LLM processing
- Continues processing remaining emails on errors
- Prints detailed error messages

**Output**:
- Progress messages for each step
- Processing status for each meeting note
- Error messages for failed extractions

**Execution**:
```bash
python scripts/run_hfn_pipeline.py
```

---

## 🗄️ Database Schema

### Table: `hfn_daily_standup_notes`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Auto-incrementing unique identifier |
| `meeting_date` | DATE | UNIQUE, NOT NULL | Date of the meeting (YYYY-MM-DD) |
| `requirements` | TEXT | | Extracted requirements from notes |
| `tech_stack` | TEXT | | Technology stack mentioned |
| `discussions` | TEXT | | Key discussion points |
| `blockers` | TEXT | | Blockers or impediments identified |
| `conclusions` | TEXT | | Conclusions or action items |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Record creation timestamp |

**Unique Constraint**: `meeting_date` ensures only one record per date.

**SQL Schema** (from `storage/schema.sql`):
```sql
CREATE TABLE IF NOT EXISTS hfn_daily_standup_notes (
    id SERIAL PRIMARY KEY,
    meeting_date DATE,
    requirements TEXT,
    tech_stack TEXT,
    discussions TEXT,
    blockers TEXT,
    conclusions TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (meeting_date)
);
```

---

## 🔧 Usage

### Running the Pipeline

Execute the main pipeline script:

```bash
python scripts/run_hfn_pipeline.py
```

### Expected Output

```
🚀 Pipeline script started
Fetching HFN Daily Standup mails...
Running HFN Notes -> LLM -> Postgres pipeline...

Processing 2024-01-15 | Daily Standup Notes - January 15
Raw LLM Output: {"meeting_date": "2024-01-15", ...}
LLM output: {'meeting_date': '2024-01-15', 'requirements': '...', ...}
Inserting into Postgres...
Stored in Postgres
```

### Testing Individual Components

**Test Google Docs Reader**:
```bash
python scripts/test_docs_reader.py
```

**Note**: Update `test_docs_reader.py` with a valid document ID.

---

## 📋 Dependencies

### Python Packages

- **google-api-python-client**: Google APIs client library
- **google-auth**: Google authentication library
- **google-auth-oauthlib**: OAuth 2.0 client for Google APIs
- **google-auth-httplib2**: HTTP transport for Google auth
- **requests**: HTTP library (legacy, may not be needed)
- **psycopg2-binary**: PostgreSQL adapter for Python
- **python-dateutil**: Date parsing utilities
- **openai**: OpenAI API client (required, add to requirements.txt)
- **python-dotenv**: Environment variable management (required, add to requirements.txt)

### External Services

- **Google Cloud Platform**: Gmail API and Google Docs API
- **OpenAI API**: For LLM-based data extraction
- **PostgreSQL**: Database server

### System Requirements

- Python 3.8+
- PostgreSQL 12+ (recommended)
- Internet connection for API calls

---

## 🔐 Security Considerations

1. **Credentials Storage**:
   - Never commit `raj_anna_credentials.json` to version control
   - Never commit `token.pickle` to version control
   - Never commit `.env` file to version control
   - Add these files to `.gitignore`

2. **API Keys**:
   - Store OpenAI API key in `.env` file
   - Use environment variables for sensitive data
   - Rotate keys if compromised

3. **Database Credentials**:
   - Consider moving database credentials to environment variables
   - Use strong passwords for production databases
   - Restrict database access to necessary IPs

4. **OAuth Tokens**:
   - `token.pickle` contains sensitive authentication tokens
   - Keep this file secure and private
   - Tokens auto-refresh, but monitor for unauthorized access

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "OPENAI_API_KEY not found in environment variables"

**Solution**:
- Create a `.env` file in the project root
- Add: `OPENAI_API_KEY=your_key_here`
- Ensure `python-dotenv` is installed: `pip install python-dotenv`

#### 2. "No module named 'openai'"

**Solution**:
```bash
pip install openai
```

#### 3. Google OAuth Authentication Fails

**Solution**:
- Verify `raj_anna_credentials.json` exists in `auth/` directory
- Check that Gmail and Google Docs APIs are enabled in Google Cloud Console
- Delete `token.pickle` and re-authenticate
- Verify OAuth scopes are correct

#### 4. "No valid JSON found in LLM output"

**Solution**:
- Check OpenAI API key is valid and has credits
- Review the "Raw LLM Output" in console
- Try adjusting the prompt in `llm/ollama_client.py`
- Consider using a different OpenAI model

#### 5. PostgreSQL Connection Errors

**Solution**:
- Verify PostgreSQL is running: `pg_isready`
- Check credentials in `storage/postgres_client.py`
- Ensure database `hfn_notes` exists
- Verify network connectivity to database

#### 6. "No document ID found in email"

**Solution**:
- Verify email contains a Google Docs link
- Check email format hasn't changed
- Review `extract_notes_doc_id()` function
- Ensure email HTML body is being parsed correctly

#### 7. Import Errors

**Solution**:
- Ensure virtual environment is activated
- Install all dependencies: `pip install -r requirements.txt`
- Check Python path is set correctly in `run_hfn_pipeline.py`

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
│  Filter Notes   │
│  Emails Only    │
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
│  Validate &     │
│  Normalize Data │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PostgreSQL     │
│  Store Data     │
└─────────────────┘
```

---

## 📝 Notes

- The project was originally designed to use Ollama (local LLM), but has been migrated to OpenAI
- The file `llm/ollama_client.py` still has "ollama" in the name but uses OpenAI
- Consider renaming the file to `openai_client.py` for clarity
- The `requirements.txt` still lists `ollama` - consider updating it
- Email processing is chronological (oldest first) to maintain order
- Duplicate meeting dates are automatically skipped via database constraint

---

## 🚧 Future Enhancements

Potential improvements for the project:

1. **Error Recovery**: Implement retry logic for API failures
2. **Logging**: Add comprehensive logging instead of print statements
3. **Configuration Management**: Move all config to environment variables or config file
4. **Testing**: Add unit tests for each module
5. **Batch Processing**: Process multiple emails in parallel
6. **Data Validation**: Enhanced validation for extracted data
7. **Monitoring**: Add monitoring and alerting for pipeline failures
8. **API Endpoints**: Create REST API to query stored meeting notes
9. **Web Interface**: Build a dashboard to view and search meeting notes
10. **Incremental Updates**: Only process new emails since last run

---

## 📄 License

[Specify your license here]

---

## 👥 Contributors

[Add contributor information]

---

## 📧 Contact

[Add contact information]

---

**Last Updated**: [Current Date]
