"""
README Generator Module
Uses OpenAI's LLM to generate a professional project README from aggregated meeting data.

This is a SEPARATE LLM module from the ingestion LLM (ollama_client.py).
It focuses exclusively on README synthesis from structured project data.
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


# Known data categories and their display labels
CATEGORY_MAP = {
    'requirements': 'Requirements',
    'tech_stack': 'Tech Stack',
    'discussions': 'Discussions',
    'blockers': 'Blockers',
    'conclusions': 'Conclusions & Action Items',
    'meeting_context': 'Meeting Context',
}

# Columns to skip when aggregating (metadata, not content)
SKIP_COLUMNS = {'id', 'meeting_date', 'created_at', 'meeting_context'}


class ReadmeGenerator:
    """
    Generates a professional README.md for a project by:
    1. Aggregating all meeting data chronologically
    2. Grouping by logical categories
    3. Synthesizing via LLM into a clean, human-readable document
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize README generator with its own OpenAI client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name (default: gpt-4o-mini)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model

        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. "
                "Set OPENAI_API_KEY in .env file or pass api_key parameter."
            )

    def _call_llm(self, messages: list, temperature: float = 0.4,
                  max_tokens: int = 4096) -> str:
        """
        Call OpenAI API for README generation.

        Args:
            messages: Chat messages
            temperature: Generation temperature (slightly higher for creative writing)
            max_tokens: Max output tokens (READMEs can be longer)

        Returns:
            str: LLM response text
        """
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=180
        )

        return response.choices[0].message.content

    def aggregate_meeting_data(self, rows: List[Dict],
                                columns: List[str]) -> Dict:
        """
        Aggregate meeting data across all rows, grouped by category.

        Produces a structured dict:
        {
            "date_range": {"earliest": "2025-01-01", "latest": "2025-06-01"},
            "meeting_count": 15,
            "meetings": [                          # chronological list
                {"date": "2025-01-01", "context": "sync", ...},
                ...
            ],
            "categories": {
                "requirements": [
                    {"date": "2025-01-01", "content": "..."},
                    ...
                ],
                "tech_stack": [...],
                ...
            },
            "extra_columns": {
                "some_custom_field": [
                    {"date": "...", "content": "..."},
                ]
            }
        }

        Args:
            rows: List of row dicts from the project table
            columns: List of column names

        Returns:
            dict: Aggregated data structure
        """
        if not rows:
            return {
                'date_range': {'earliest': None, 'latest': None},
                'meeting_count': 0,
                'meetings': [],
                'categories': {},
                'extra_columns': {},
            }

        # Collect all dates for range
        dates = []
        for row in rows:
            d = row.get('meeting_date')
            if d:
                dates.append(str(d))

        date_range = {
            'earliest': min(dates) if dates else None,
            'latest': max(dates) if dates else None,
        }

        # Identify content columns
        known_categories = set(CATEGORY_MAP.keys())
        content_columns = [
            c for c in columns
            if c not in SKIP_COLUMNS and c != 'meeting_date'
        ]

        # Build per-category aggregation
        categories = {}
        extra_columns = {}

        for col in content_columns:
            entries = []
            for row in rows:
                val = row.get(col)
                if val and str(val).strip() and str(val).strip().lower() != 'none':
                    entries.append({
                        'date': str(row.get('meeting_date', 'Unknown')),
                        'context': row.get('meeting_context', ''),
                        'content': str(val).strip(),
                    })

            if not entries:
                continue

            if col in known_categories:
                categories[col] = entries
            else:
                extra_columns[col] = entries

        # Build chronological meeting list
        meetings = []
        for row in rows:
            meeting = {
                'date': str(row.get('meeting_date', 'Unknown')),
                'context': row.get('meeting_context', ''),
            }
            for col in content_columns:
                val = row.get(col)
                if val and str(val).strip() and str(val).strip().lower() != 'none':
                    meeting[col] = str(val).strip()
            meetings.append(meeting)

        return {
            'date_range': date_range,
            'meeting_count': len(rows),
            'meetings': meetings,
            'categories': categories,
            'extra_columns': extra_columns,
        }

    def _build_system_prompt(self) -> str:
        """Build the system prompt for README generation."""
        return """You are a senior technical writer and software architect.

Your task is to synthesize raw meeting data from a software project into a polished, 
professional README.md document.

RULES:
- Write like a real engineering README, NOT like meeting minutes.
- Summarize recurring themes across meetings. Do NOT list each meeting separately.
- Merge duplicate or overlapping points into concise statements.
- Highlight how requirements, decisions, or tech stack evolved over time when relevant.
- Use clean, professional markdown formatting.
- Be concise but complete. Avoid filler language.
- Do NOT include phrases like "as discussed in the meeting on..." or "per the sync call..."
- Transform raw discussion points into actionable, reader-friendly content.
- If data is sparse or missing for a section, write a brief note rather than omitting the section.
- Output ONLY the markdown content. No preamble, no explanation, no code fences wrapping the entire output."""

    def _build_user_prompt(self, project_name: str,
                           aggregated: Dict) -> str:
        """
        Build the user prompt with all aggregated project data.

        Args:
            project_name: Display name of the project
            aggregated: Aggregated data dict from aggregate_meeting_data()

        Returns:
            str: User prompt
        """
        date_range = aggregated['date_range']
        meeting_count = aggregated['meeting_count']
        categories = aggregated['categories']
        extra_columns = aggregated['extra_columns']

        lines = []
        lines.append(f"PROJECT: {project_name}")
        lines.append(f"DATA SOURCE: {meeting_count} meetings/discussions")

        if date_range['earliest'] and date_range['latest']:
            lines.append(f"DATE RANGE: {date_range['earliest']} to {date_range['latest']}")

        lines.append("")
        lines.append("=" * 60)
        lines.append("AGGREGATED MEETING DATA BY CATEGORY")
        lines.append("=" * 60)

        # Known categories
        for cat_key, cat_label in CATEGORY_MAP.items():
            if cat_key in categories:
                entries = categories[cat_key]
                lines.append(f"\n--- {cat_label.upper()} ({len(entries)} entries) ---")
                for entry in entries:
                    date_str = entry['date']
                    ctx = f" [{entry['context']}]" if entry.get('context') else ""
                    lines.append(f"  [{date_str}{ctx}] {entry['content']}")

        # Extra/dynamic columns
        if extra_columns:
            lines.append(f"\n--- ADDITIONAL DATA ---")
            for col_name, entries in extra_columns.items():
                display_name = col_name.replace('_', ' ').title()
                lines.append(f"\n  {display_name} ({len(entries)} entries):")
                for entry in entries:
                    date_str = entry['date']
                    lines.append(f"    [{date_str}] {entry['content']}")

        lines.append("")
        lines.append("=" * 60)
        lines.append("REQUIRED OUTPUT FORMAT")
        lines.append("=" * 60)
        lines.append("""
Generate a README.md with EXACTLY these sections in this order:

# {Project Name}

## Project Overview
A concise 2-3 paragraph summary of what this project is about.

## Problem Statement
What problem does this project solve? Why does it exist?

## Requirements Summary
Consolidated requirements, organized logically (not chronologically).

## Tech Stack
Technologies, frameworks, tools, and infrastructure involved.

## Key Discussions
Major technical or product discussions that shaped the project.
Summarize themes, don't list individual meetings.

## Decisions & Outcomes
Key decisions made, and their rationale where available.

## Blockers & Risks
Known blockers, risks, or impediments (past and current).

## Current Status
Where the project stands now based on the latest data.

## Open Questions / Next Steps
Unresolved questions and planned next actions.
""")

        return "\n".join(lines)

    def generate(self, project_name: str, rows: List[Dict],
                 columns: List[str]) -> str:
        """
        Generate a professional README.md from meeting data.

        Args:
            project_name: Display name (e.g. "ACT")
            rows: List of row dicts from the project table (chronological)
            columns: List of column names

        Returns:
            str: Generated README markdown content
        """
        # Step 1: Aggregate data
        print(f"  [1/3] Aggregating data from {len(rows)} meeting(s)...")
        aggregated = self.aggregate_meeting_data(rows, columns)

        if aggregated['meeting_count'] == 0:
            return self._empty_readme(project_name)

        # Step 2: Build prompts
        print(f"  [2/3] Generating README via LLM ({self.model})...")
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(project_name, aggregated)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Step 3: Call LLM
        readme_content = self._call_llm(messages, temperature=0.4, max_tokens=4096)

        # Clean up: remove any wrapping code fences the LLM might add
        readme_content = self._strip_code_fences(readme_content)

        print(f"  [3/3] README generated ({len(readme_content)} characters)")
        return readme_content

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove wrapping ```markdown ... ``` if present."""
        text = text.strip()
        if text.startswith('```'):
            # Remove opening fence
            first_newline = text.find('\n')
            if first_newline != -1:
                text = text[first_newline + 1:]
        if text.endswith('```'):
            text = text[:-3].rstrip()
        return text.strip()

    @staticmethod
    def _empty_readme(project_name: str) -> str:
        """Generate a placeholder README for projects with no data."""
        return f"""# {project_name}

## Project Overview

No meeting data available yet for this project.

## Status

This README will be automatically populated once meeting data is ingested.
"""

    def save_to_disk(self, project_name: str, content: str,
                     output_dir: str = "readmes") -> str:
        """
        Save generated README to disk.

        Args:
            project_name: Project name (used in filename)
            content: README markdown content
            output_dir: Output directory (default: readmes/)

        Returns:
            str: Path to saved file
        """
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Sanitize filename
        safe_name = project_name.lower().replace(' ', '_')
        safe_name = ''.join(c if c.isalnum() or c == '_' else '' for c in safe_name)
        filename = f"README_{safe_name}.md"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath
