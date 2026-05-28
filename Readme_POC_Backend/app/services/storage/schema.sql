-- PostgreSQL Schema for Multi-Project Meeting Notes System
-- This file is for reference only. Tables are created dynamically.

-- Master metadata table for projects
CREATE TABLE IF NOT EXISTS projects_metadata (
    project_name VARCHAR(255) PRIMARY KEY,
    normalized_name VARCHAR(255) UNIQUE NOT NULL,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50) DEFAULT 'gmail',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


