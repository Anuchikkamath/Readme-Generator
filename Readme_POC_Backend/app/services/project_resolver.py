"""
Project Resolver Module
Canonicalizes project names from email subjects using generic normalization.
Uses learning-based resolution with database-backed project metadata.
Ensures ONE table per canonical project (prevents table explosion).

Key Design:
- The project name is the FIRST word/acronym in the subject (after "Notes:")
- Everything after the project identifier is treated as meeting context
- Database prefix matching ensures consistent resolution across variants
- Prevents table explosion: all ACT emails → one "act" table

Examples:
    "Notes: ACT sync"                      → Canonical: "ACT"       → Table: "act"
    "Notes: ACT Internal Discussion"       → Canonical: "ACT"       → Table: "act"
    "Notes: ACT Questions and Discussions"  → Canonical: "ACT"       → Table: "act"
    "Notes: ACT Proejct"                   → Canonical: "ACT"       → Table: "act"
    "Notes: Hackathon Early Dev Brief"     → Canonical: "Hackathon" → Table: "hackathon"
    "Notes: GSE-COM 1 Series Voucher..."   → Canonical: "GSE-COM"   → Table: "gse_com"
"""

import re
from typing import Optional, Tuple, List
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()


class ProjectResolver:
    """
    Resolves canonical project names from email subjects.
    Uses first-word extraction + database prefix matching.
    """
    
    # Context stopwords - when encountered, STOP: everything from here is context, NOT project name.
    # The project identifier consists of leading words BEFORE the first stopword.
    CONTEXT_STOPWORDS = {
        # Meeting types
        'sync', 'syncing', 'synced',
        'discussion', 'discussions',
        'meeting', 'meetings', 'standup', 'standups',
        'internal', 'external',
        'review', 'reviews', 'retrospective',
        'update', 'updates', 'updated',
        'notes', 'note',
        'daily', 'weekly', 'monthly', 'quarterly',
        'workshop', 'workshops',
        'brief', 'briefing',
        'call', 'calls',
        'session', 'sessions',
        'sprint', 'sprints',
        'planning', 'grooming', 'refinement',
        
        # Project descriptors (not part of project identity)
        'project', 'proejct',  # include common typo
        'questions', 'question',
        'demo', 'demos', 'demonstration',
        'early', 'late',
        'dev', 'development', 'developer',
        'series',
        'code', 'coding',
        'handling', 'handler',
        'overview', 'summary',
        'status', 'report',
        'kickoff', 'kick-off',
        'onboarding',
        'walkthrough',
        'deep', 'dive',
        'tech', 'technical',
        'design', 'architecture',
        'feature', 'features',
        'bug', 'bugs', 'fix', 'fixes',
        'release', 'deployment',
        'testing', 'test', 'tests',
        'integration',
        'performance', 'optimization',
        'voucher', 'vouchers',
        'implementation',
        'setup', 'config', 'configuration',
        'migration', 'migrating',
        'documentation', 'docs',
        'api', 'endpoint', 'endpoints',
        'frontend', 'backend', 'fullstack',
        'database', 'db',
        'ui', 'ux',
        'roadmap', 'timeline',
        
        # Common English filler/connector words
        'and', 'or', 'the', 'a', 'an',
        'in', 'on', 'at', 'to', 'of', 'for', 'with', 'by', 'from',
        'is', 'was', 'are', 'were', 'be', 'been', 'being',
        'has', 'have', 'had', 'having',
        'do', 'does', 'did', 'doing',
        'will', 'would', 'shall', 'should',
        'can', 'could', 'may', 'might',
        'this', 'that', 'these', 'those',
        'all', 'each', 'every', 'some', 'any', 'no', 'not',
        'new', 'old', 'latest', 'recent',
        'about', 'around', 'between',
        'follow', 'up', 'followup', 'follow-up',
        
        # Numbers (rarely part of project identity alone)
        '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
        'first', 'second', 'third',
        '1st', '2nd', '3rd',
    }
    
    # Separators that split project name from context
    CONTEXT_SEPARATORS = ['::', ' - ', ' | ', ' / ', ' -', '- ', '|', '/']
    
    def __init__(self):
        """Initialize project resolver (no DB connection at init time)."""
        self.db_name = os.getenv('DB_NAME', 'projects')
    
    def _get_connection(self):
        """Get database connection."""
        return psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            database=self.db_name
        )
    
    @staticmethod
    def _extract_base_from_subject(subject: str) -> Optional[str]:
        """
        Extract base project string from email subject.
        Removes "Notes:" prefix and trailing date patterns.
        
        Args:
            subject: Email subject line
            
        Returns:
            str: Base project string, or None
        """
        if not subject:
            return None
        
        # Check if subject contains "Notes:"
        if 'Notes:' not in subject and 'notes:' not in subject:
            # STRICT MODE: If it doesn't start with Notes:, it's not a meeting note
            return None
        
        # Split on "Notes: " (case insensitive)
        parts = re.split(r'Notes:\s*', subject, flags=re.IGNORECASE, maxsplit=1)
        if len(parts) < 2:
            return None
        
        # Get everything after "Notes: "
        after_notes = parts[1].strip()
        
        # If subject was just "Notes: ", return None
        if not after_notes:
            return None
        
        after_notes = after_notes.strip('"\'\u201c\u201d\u2018\u2019')
        
        # Remove date patterns (month names, numeric dates, ISO dates)
        month_pattern = (
            r'\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
            r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b'
        )
        date_pattern = r'\s+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'
        iso_date_pattern = r'\s+\d{4}[/-]\d{1,2}[/-]\d{1,2}'
        
        # Find earliest date pattern
        matches = []
        for pattern in [month_pattern, date_pattern, iso_date_pattern]:
            m = re.search(pattern, after_notes, re.IGNORECASE)
            if m:
                matches.append(m.start())
        
        if matches:
            cut_point = min(matches)
            base = after_notes[:cut_point].strip()
        else:
            base = after_notes.strip()
        
        base = base.strip(' "\'\u201c\u201d\u2018\u2019,.-')
        return base if base else None
    
    @staticmethod
    def _canonicalize_project_name(base_string: str) -> str:
        """
        Extract the CORE project identifier from base string.
        
        Strategy:
        1. Split on context separators (::, -, |, /) and take first part
        2. Take leading non-stopword words as project identifier
        3. STOP at first stopword → everything after is context
        
        This ensures:
            "ACT sync"                      → "ACT"
            "ACT - Internal Discussion"     → "ACT"
            "ACT::Sync"                     → "ACT"
            "ACT Questions and Discussions" → "ACT"
            "ACT Proejct"                   → "ACT"
            "Hackathon Early Dev Brief"     → "Hackathon"
            "GSE-COM 1 Series Voucher..."   → "GSE-COM"
        
        Args:
            base_string: Base project string from subject
            
        Returns:
            str: Canonical project name (core identifier only)
        """
        if not base_string:
            return "unknown_project"
        
        text = base_string.strip()
        
        # Step 1: Split on context separators, take first part
        for separator in ProjectResolver.CONTEXT_SEPARATORS:
            if separator in text:
                text = text.split(separator, 1)[0].strip()
                break
        
        # Step 2: Split into words
        words = text.split()
        if not words:
            return "unknown_project"
        
        # Step 3: Take leading words until we hit a stopword
        # The project identifier = everything BEFORE the first stopword
        project_words = []
        for word in words:
            if word.lower() in ProjectResolver.CONTEXT_STOPWORDS:
                break  # STOP at first context word
            project_words.append(word)
        
        # If ALL words were stopwords, use first word as fallback
        if not project_words:
            project_words = [words[0]]
        
        canonical = ' '.join(project_words).strip()
        return canonical if canonical else "unknown_project"
    
    @staticmethod
    def normalize_table_name(canonical_name: str) -> str:
        """
        Normalize canonical project name to valid PostgreSQL table name.
        
        Args:
            canonical_name: Canonical project name
            
        Returns:
            str: Normalized table name (lowercase, underscores)
        """
        if not canonical_name:
            return "unknown_project"
        
        # Convert to lowercase
        normalized = canonical_name.lower().strip()
        
        # Replace special chars with underscores
        normalized = re.sub(r'[^a-z0-9_]+', '_', normalized)
        
        # Remove multiple consecutive underscores
        normalized = re.sub(r'_+', '_', normalized)
        
        # Remove leading/trailing underscores
        normalized = normalized.strip('_')
        
        # Ensure starts with letter
        if normalized and not normalized[0].isalpha():
            normalized = 'p_' + normalized
        
        # Ensure not empty
        if not normalized:
            normalized = 'unknown_project'
        
        # PostgreSQL identifier limit is 63 chars
        if len(normalized) > 63:
            normalized = normalized[:63]
        
        return normalized
    
    @staticmethod
    def extract_context_from_subject(subject: str, canonical_project: str) -> Optional[str]:
        """
        Extract meeting context from subject (sync, discussion, etc.).
        Context = everything in the subject that isn't the project name or dates.
        
        Args:
            subject: Email subject line
            canonical_project: Canonical project name
            
        Returns:
            str: Context string (e.g., "sync", "internal discussion"), or None
        """
        if not subject or not canonical_project:
            return None
        
        # Extract base string
        base = ProjectResolver._extract_base_from_subject(subject)
        if not base:
            return None
        
        # Remove canonical project name (case-insensitive)
        base_lower = base.lower()
        canonical_lower = canonical_project.lower()
        
        if canonical_lower in base_lower:
            # Remove project name
            remainder = base_lower.replace(canonical_lower, '', 1).strip()
            
            # Clean up separators
            for sep in ProjectResolver.CONTEXT_SEPARATORS:
                remainder = remainder.replace(sep.lower(), ' ').strip()
            remainder = re.sub(r'^[-|/:\s]+|[-|/:\s]+$', '', remainder).strip()
            
            if remainder:
                # Return the full context (not just stopwords)
                return remainder.strip()
        
        return None
    
    def resolve_by_participants(self, participants: List[str]) -> Optional[Tuple[str, str]]:
        """
        Find an existing project that shares significant participants with the provided list.
        
        Args:
            participants: List of email addresses from current meeting
            
        Returns:
            tuple: (canonical_name, normalized_name) or None
        """
        if not participants:
            return None
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Fetch all projects with their participants
            cursor.execute("SELECT canonical_name, normalized_name, participants FROM projects_metadata WHERE participants IS NOT NULL")
            all_projects = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            current_participants = set(p.lower() for p in participants if p)
            if not current_participants:
                return None
                
            best_match = None
            max_overlap = 0
            
            for canonical, normalized, project_participants in all_projects:
                if not project_participants:
                    continue
                    
                project_set = set(p.lower() for p in project_participants if p)
                # Calculate overlap
                overlap = len(current_participants.intersection(project_set))
                
                # If there's an overlap, consider it a candidate
                # We want at least 2 participants overlap (or 100% if only 1 participant total in current)
                threshold = 1 if len(current_participants) == 1 else 2
                
                if overlap >= threshold and overlap > max_overlap:
                    max_overlap = overlap
                    best_match = (canonical, normalized)
            
            if best_match:
                print(f"    [OK] Matched project '{best_match[0]}' via participants (overlap: {max_overlap})")
            
            return best_match
            
        except Exception as e:
            print(f"[WARN] Error during participant resolution: {e}")
            return None

    def resolve_canonical_project(self, email_subject: str, 
                                  llm_extracted_name: Optional[str] = None,
                                  participants: Optional[List[str]] = None) -> Tuple[str, str]:
        """
        Resolve canonical project name with database-backed learning and prefix matching.
        
        Process:
        1. Extract base string from subject
        2. IF base is generic (Demo, Sync), try resolution by participants
        3. Canonicalize (extract first word/acronym, remove context)
        4. Normalize for table name
        5. Check database:
           a) Exact match → reuse existing
           b) Existing is prefix of candidate → reuse existing
           c) Candidate is prefix of existing → consolidate
           d) No match → register new project
        """
        # Step 1: Extract base string
        base_string = self._extract_base_from_subject(email_subject)
        
        # Step 2: Handle generic subjects using participants
        if base_string and base_string.lower() in ['demo', 'demos', 'sync', 'syncing', 'meeting', 'notes']:
            print(f"    > Generic subject '{base_string}' detected, attempting participant match...")
            participant_match = self.resolve_by_participants(participants or [])
            if participant_match:
                return participant_match
        
        # Step 3: Canonicalize
        if base_string:
            canonical = self._canonicalize_project_name(base_string)
        elif llm_extracted_name:
            canonical = self._canonicalize_project_name(llm_extracted_name)
        else:
            canonical = "Unknown Project"
        
        # Step 4: Normalize for table name
        normalized = self.normalize_table_name(canonical)
        
        print(f"    > Project resolution: subject='{email_subject}' -> canonical='{canonical}' -> table='{normalized}'")
        
        # Step 5: Database lookup with prefix matching
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Fetch all existing projects for matching
            cursor.execute("SELECT canonical_name, normalized_name FROM projects_metadata")
            all_projects = cursor.fetchall()
            
            # a) Exact match on normalized name
            for ec, en in all_projects:
                if en == normalized:
                    self._update_last_seen(cursor, ec, email_subject)
                    conn.commit()
                    cursor.close()
                    conn.close()
                    print(f"    [OK] Matched existing project: '{ec}' (exact)")
                    return (ec, en)
            
            # b) Existing is prefix of candidate
            best_match = None
            for ec, en in all_projects:
                if normalized.startswith(en + '_'):
                    if best_match is None or len(en) > len(best_match[1]):
                        best_match = (ec, en)
            
            if best_match:
                self._update_last_seen(cursor, best_match[0], email_subject)
                conn.commit()
                cursor.close()
                conn.close()
                print(f"    [OK] Matched existing project: '{best_match[0]}' (prefix match)")
                return best_match
            
            # c) Candidate is prefix of existing
            matches = [(ec, en) for ec, en in all_projects if en.startswith(normalized + '_')]
            if matches:
                print(f"    > Consolidating {len(matches)} old entries into '{canonical}' ({normalized})")
                for ec, en in matches:
                    cursor.execute(
                        "DELETE FROM projects_metadata WHERE canonical_name = %s", 
                        (ec,)
                    )
                
                cursor.execute("""
                    INSERT INTO projects_metadata 
                    (canonical_name, normalized_name, example_subjects)
                    VALUES (%s, %s, ARRAY[%s])
                    ON CONFLICT (canonical_name) DO UPDATE SET
                        last_seen_at = CURRENT_TIMESTAMP
                """, (canonical, normalized, email_subject[:200]))
                conn.commit()
                cursor.close()
                conn.close()
                return (canonical, normalized)
            
            # d) No match → register new project
            cursor.execute("""
                INSERT INTO projects_metadata 
                (canonical_name, normalized_name, example_subjects)
                VALUES (%s, %s, ARRAY[%s])
                ON CONFLICT (canonical_name) DO UPDATE SET
                    last_seen_at = CURRENT_TIMESTAMP
            """, (canonical, normalized, email_subject[:200]))
            conn.commit()
            cursor.close()
            conn.close()
            print(f"    [OK] Registered new project: '{canonical}' ({normalized})")
            
        except Exception as e:
            print(f"[WARN] Could not update project metadata: {e}")
        
        return (canonical, normalized)
    
    def _update_last_seen(self, cursor, canonical_name: str, email_subject: str):
        """Update last_seen_at and add example subject for a project."""
        try:
            cursor.execute("""
                UPDATE projects_metadata 
                SET last_seen_at = CURRENT_TIMESTAMP,
                    example_subjects = (
                        SELECT array_agg(DISTINCT s) 
                        FROM unnest(
                            array_append(
                                COALESCE(example_subjects, ARRAY[]::TEXT[]),
                                %s
                            )
                        ) AS s
                    )
                WHERE canonical_name = %s
            """, (email_subject[:200], canonical_name))
        except Exception:
            cursor.execute("""
                UPDATE projects_metadata 
                SET last_seen_at = CURRENT_TIMESTAMP
                WHERE canonical_name = %s
            """, (canonical_name,))
    
    def get_canonical_project(self, normalized_name: str) -> Optional[str]:
        """
        Get canonical project name from normalized name.
        
        Args:
            normalized_name: Normalized table name
            
        Returns:
            str: Canonical project name, or None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT canonical_name FROM projects_metadata WHERE normalized_name = %s",
                (normalized_name,)
            )
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return result[0] if result else None
            
        except Exception:
            return None
