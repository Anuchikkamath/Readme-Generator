# Architecture Documentation

## Overview

This codebase follows a modular architecture that processes meeting notes from Gmail for multiple projects. The system automatically detects projects, extracts structured data, and stores it in PostgreSQL with dynamic table creation.

## Directory Structure

```
.
├── auth/                    # Authentication layer
│   ├── __init__.py
│   └── token_gen.py        # Google OAuth token management
│
├── ingestion/              # Email ingestion layer
│   ├── __init__.py
│   ├── gmail_reader.py     # Gmail API client
│   └── body_parser.py      # Email body parsing
│
├── documents/              # Document retrieval layer
│   ├── __init__.py
│   └── docs_reader.py     # Google Docs API client
│
├── llm/                    # LLM processing layer
│   ├── __init__.py
│   └── ollama_client.py    # OpenAI client for extraction
│
├── storage/                # Storage layer
│   ├── __init__.py
│   ├── postgres_client.py  # PostgreSQL operations
│   └── schema.sql          # Schema reference
│
├── scripts/                # Execution scripts
│   └── run_pipeline.py     # Main pipeline
│
├── project_resolver.py     # Project detection & normalization
├── schema_manager.py       # Dynamic schema management
├── requirements.txt        # Dependencies
└── README.md              # Main documentation
```

## Data Flow

```
┌─────────────┐
│  Gmail API  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Gmail Reader   │  ← ingestion/gmail_reader.py
│  Fetch Emails   │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Body Parser    │  ← ingestion/body_parser.py
│  Extract Doc ID │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Project        │  ← project_resolver.py
│  Resolver       │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Docs Reader    │  ← documents/docs_reader.py
│  Fetch Content  │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  LLM Client     │  ← llm/ollama_client.py
│  Extract Data   │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Schema Manager │  ← schema_manager.py
│  Manage Tables  │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Postgres Client│  ← storage/postgres_client.py
│  Store Data     │
└─────────────────┘
```

## Key Design Decisions

### 1. Modular Architecture
- Each layer has a single responsibility
- Clear separation between ingestion, processing, and storage
- Easy to test and maintain

### 2. Dynamic Schema Management
- Tables created on-demand for each project
- Schema evolves automatically as LLM output changes
- Never drops columns (data preservation)

### 3. Project Detection
- Extracts project names from email subjects
- Falls back to LLM extraction if subject parsing fails
- Normalizes names for database compatibility

### 4. Idempotency
- Safe to run multiple times
- Duplicate detection via database constraints
- Automatic schema updates without data loss

## Database Design

### Master Table: `projects_metadata`
- Tracks all detected projects
- Stores original and normalized names
- Tracks first seen and last processed timestamps

### Project Tables (Dynamic)
- One table per project (normalized name)
- Base columns: `id`, `meeting_date`, `created_at`
- Additional columns from LLM output (TEXT type)

## Environment Variables

Required environment variables (in `.env` file):

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=projects
DB_ADMIN_DB=postgres

# OpenAI
OPENAI_API_KEY=your_key_here

# Google OAuth (optional)
GOOGLE_CREDENTIALS_FILE=readme_credentials.json
GOOGLE_TOKEN_FILE=token.pickle
```

## Execution Flow

1. **Initialization**: Load credentials, initialize clients
2. **Email Fetching**: Get all "Notes:" emails from Gmail
3. **Project Grouping**: Group emails by detected project
4. **Processing**: For each project:
   - Extract document IDs
   - Fetch document content
   - Extract structured data via LLM
   - Store in project table
5. **Summary**: Report statistics and registered projects

## Error Handling

- Continues processing on individual email failures
- Logs errors with context
- Skips emails without document links
- Handles missing project names gracefully

## Future Enhancements

- Parallel processing for multiple projects
- Retry logic for API failures
- Comprehensive logging system
- Web interface for viewing data
- REST API for querying stored notes
