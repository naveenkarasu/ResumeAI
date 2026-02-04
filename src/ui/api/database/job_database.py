"""SQLite database for Job List feature"""

import sqlite3
import json
import uuid
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class JobDatabase:
    """SQLite database manager for job listings and applications"""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("data/jobs.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Schema version tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                )
            """)

            # Check current version
            cursor.execute("SELECT version FROM schema_version")
            row = cursor.fetchone()
            current_version = row[0] if row else 0

            if current_version < self.SCHEMA_VERSION:
                self._create_schema(cursor)
                cursor.execute("DELETE FROM schema_version")
                cursor.execute("INSERT INTO schema_version (version) VALUES (?)",
                               (self.SCHEMA_VERSION,))
                logger.info(f"Database schema updated to version {self.SCHEMA_VERSION}")

    def _create_schema(self, cursor):
        """Create all database tables"""

        # Companies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                normalized_name TEXT UNIQUE NOT NULL,
                logo_url TEXT,
                website TEXT,
                industry TEXT,
                size TEXT CHECK(size IN ('startup', 'small', 'medium', 'large', 'enterprise')),
                rating REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(normalized_name)")

        # Jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                company_id TEXT REFERENCES companies(id),
                location TEXT,
                location_type TEXT CHECK(location_type IN ('remote', 'hybrid', 'onsite')),
                salary_min INTEGER,
                salary_max INTEGER,
                salary_currency TEXT DEFAULT 'USD',
                salary_text TEXT,
                description TEXT NOT NULL,
                requirements TEXT,
                posted_date DATE,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                embedding_id TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(location_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_salary ON jobs(salary_min, salary_max)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_posted ON jobs(posted_date DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs(is_active)")

        # Applications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                job_id TEXT UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
                status TEXT NOT NULL CHECK(status IN (
                    'saved', 'applied', 'screening', 'interview',
                    'offer', 'rejected', 'withdrawn', 'accepted'
                )),
                applied_date DATE,
                notes TEXT,
                resume_version TEXT,
                cover_letter TEXT,
                reminder_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_reminder ON applications(reminder_date)")

        # Application timeline
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_timeline (
                id TEXT PRIMARY KEY,
                application_id TEXT REFERENCES applications(id) ON DELETE CASCADE,
                old_status TEXT,
                new_status TEXT NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timeline_app ON application_timeline(application_id)")

        # Saved searches
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_searches (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                query TEXT,
                filters_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_run_at TIMESTAMP,
                notification_enabled BOOLEAN DEFAULT 0
            )
        """)

        # Search cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                id TEXT PRIMARY KEY,
                query_hash TEXT UNIQUE NOT NULL,
                filters_json TEXT NOT NULL,
                result_job_ids TEXT NOT NULL,
                total_results INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_hash ON search_cache(query_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON search_cache(expires_at)")

        # Job match scores (pre-calculated)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_match_scores (
                id TEXT PRIMARY KEY,
                job_id TEXT REFERENCES jobs(id) ON DELETE CASCADE,
                resume_hash TEXT NOT NULL,
                overall_score REAL NOT NULL,
                skills_score REAL,
                experience_score REAL,
                education_score REAL,
                matched_skills TEXT,
                missing_skills TEXT,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(job_id, resume_hash)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_job ON job_match_scores(job_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_score ON job_match_scores(overall_score DESC)")

    # ============== Company Operations ==============

    def get_or_create_company(self, name: str, **kwargs) -> str:
        """Get existing company or create new one, returns company ID"""
        normalized = name.lower().strip().replace(" ", "_")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if exists
            cursor.execute(
                "SELECT id FROM companies WHERE normalized_name = ?",
                (normalized,)
            )
            row = cursor.fetchone()

            if row:
                return row[0]

            # Create new company
            company_id = f"company_{uuid.uuid4().hex[:12]}"
            cursor.execute("""
                INSERT INTO companies (id, name, normalized_name, logo_url, website, industry, size, rating)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id,
                name,
                normalized,
                kwargs.get("logo_url"),
                kwargs.get("website"),
                kwargs.get("industry"),
                kwargs.get("size"),
                kwargs.get("rating")
            ))

            return company_id

    def get_company(self, company_id: str) -> Optional[Dict]:
        """Get company by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ============== Job Operations ==============

    def insert_job(self, job_data: Dict) -> str:
        """Insert a new job, returns job ID. Skips if URL exists."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if URL already exists
            cursor.execute("SELECT id FROM jobs WHERE url = ?", (job_data["url"],))
            row = cursor.fetchone()
            if row:
                return row[0]  # Return existing job ID

            job_id = f"job_{uuid.uuid4().hex[:12]}"
            requirements_json = json.dumps(job_data.get("requirements", []))

            cursor.execute("""
                INSERT INTO jobs (
                    id, url, title, company_id, location, location_type,
                    salary_min, salary_max, salary_currency, salary_text,
                    description, requirements, posted_date, source, embedding_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job_data["url"],
                job_data["title"],
                job_data.get("company_id"),
                job_data.get("location"),
                job_data.get("location_type"),
                job_data.get("salary_min"),
                job_data.get("salary_max"),
                job_data.get("salary_currency", "USD"),
                job_data.get("salary_text"),
                job_data["description"],
                requirements_json,
                job_data.get("posted_date"),
                job_data["source"],
                job_data.get("embedding_id")
            ))

            return job_id

    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job by ID with company info"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT j.*, c.name as company_name, c.logo_url as company_logo,
                       c.industry as company_industry, c.size as company_size, c.rating as company_rating
                FROM jobs j
                LEFT JOIN companies c ON j.company_id = c.id
                WHERE j.id = ?
            """, (job_id,))
            row = cursor.fetchone()

            if not row:
                return None

            job = dict(row)
            job["requirements"] = json.loads(job.get("requirements") or "[]")
            return job

    def search_jobs(
        self,
        keywords: List[str] = None,
        location_type: List[str] = None,
        salary_min: int = None,
        salary_max: int = None,
        sources: List[str] = None,
        posted_within_days: int = 30,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "posted_date",
        sort_order: str = "desc"
    ) -> tuple[List[Dict], int]:
        """Search jobs with filters, returns (jobs, total_count)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            conditions = ["j.is_active = 1"]
            params = []

            if keywords:
                keyword_conditions = []
                for kw in keywords:
                    keyword_conditions.append("(j.title LIKE ? OR j.description LIKE ?)")
                    params.extend([f"%{kw}%", f"%{kw}%"])
                conditions.append(f"({' OR '.join(keyword_conditions)})")

            if location_type:
                placeholders = ",".join("?" * len(location_type))
                conditions.append(f"j.location_type IN ({placeholders})")
                params.extend(location_type)

            if salary_min is not None:
                conditions.append("(j.salary_max >= ? OR j.salary_max IS NULL)")
                params.append(salary_min)

            if salary_max is not None:
                conditions.append("(j.salary_min <= ? OR j.salary_min IS NULL)")
                params.append(salary_max)

            if sources:
                placeholders = ",".join("?" * len(sources))
                conditions.append(f"j.source IN ({placeholders})")
                params.extend(sources)

            if posted_within_days:
                conditions.append("j.posted_date >= date('now', ?)")
                params.append(f"-{posted_within_days} days")

            where_clause = " AND ".join(conditions)

            # Validate sort column
            valid_sorts = {"posted_date": "j.posted_date", "salary": "j.salary_max", "title": "j.title"}
            sort_col = valid_sorts.get(sort_by, "j.posted_date")
            sort_dir = "DESC" if sort_order.lower() == "desc" else "ASC"

            # Count total
            count_query = f"""
                SELECT COUNT(*) FROM jobs j
                LEFT JOIN companies c ON j.company_id = c.id
                WHERE {where_clause}
            """
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # Get results
            query = f"""
                SELECT j.*, c.name as company_name, c.logo_url as company_logo,
                       c.industry as company_industry, c.size as company_size
                FROM jobs j
                LEFT JOIN companies c ON j.company_id = c.id
                WHERE {where_clause}
                ORDER BY {sort_col} {sort_dir}
                LIMIT ? OFFSET ?
            """
            cursor.execute(query, params + [limit, offset])

            jobs = []
            for row in cursor.fetchall():
                job = dict(row)
                job["requirements"] = json.loads(job.get("requirements") or "[]")
                jobs.append(job)

            return jobs, total

    def update_job_embedding(self, job_id: str, embedding_id: str):
        """Update job's embedding reference"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE jobs SET embedding_id = ? WHERE id = ?",
                (embedding_id, job_id)
            )

    def deactivate_old_jobs(self, days: int = 60):
        """Mark jobs older than X days as inactive"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE jobs SET is_active = 0
                WHERE posted_date < date('now', ?)
            """, (f"-{days} days",))
            return cursor.rowcount

    # ============== Application Operations ==============

    def create_application(self, job_id: str, status: str = "saved", **kwargs) -> str:
        """Create or update application for a job"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if application exists
            cursor.execute("SELECT id, status FROM applications WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()

            if row:
                # Update existing
                app_id = row[0]
                old_status = row[1]
                cursor.execute("""
                    UPDATE applications SET
                        status = ?,
                        notes = COALESCE(?, notes),
                        resume_version = COALESCE(?, resume_version),
                        cover_letter = COALESCE(?, cover_letter),
                        reminder_date = COALESCE(?, reminder_date),
                        applied_date = CASE WHEN ? = 'applied' AND applied_date IS NULL THEN date('now') ELSE applied_date END,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    status,
                    kwargs.get("notes"),
                    kwargs.get("resume_version"),
                    kwargs.get("cover_letter"),
                    kwargs.get("reminder_date"),
                    status,
                    app_id
                ))

                # Add timeline entry if status changed
                if old_status != status:
                    self._add_timeline_entry(cursor, app_id, old_status, status, kwargs.get("notes"))

                return app_id

            # Create new application
            app_id = f"app_{uuid.uuid4().hex[:12]}"
            applied_date = date.today().isoformat() if status == "applied" else None

            cursor.execute("""
                INSERT INTO applications (id, job_id, status, applied_date, notes, resume_version, cover_letter, reminder_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                app_id,
                job_id,
                status,
                applied_date,
                kwargs.get("notes"),
                kwargs.get("resume_version"),
                kwargs.get("cover_letter"),
                kwargs.get("reminder_date")
            ))

            # Add initial timeline entry
            self._add_timeline_entry(cursor, app_id, None, status)

            return app_id

    def _add_timeline_entry(self, cursor, app_id: str, old_status: Optional[str], new_status: str, notes: str = None):
        """Add entry to application timeline"""
        entry_id = f"timeline_{uuid.uuid4().hex[:12]}"
        cursor.execute("""
            INSERT INTO application_timeline (id, application_id, old_status, new_status, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (entry_id, app_id, old_status, new_status, notes))

    def get_application(self, app_id: str) -> Optional[Dict]:
        """Get application with job info and timeline"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT a.*, j.title as job_title, j.url as job_url,
                       c.name as company_name, c.logo_url as company_logo
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                LEFT JOIN companies c ON j.company_id = c.id
                WHERE a.id = ?
            """, (app_id,))
            row = cursor.fetchone()

            if not row:
                return None

            app = dict(row)

            # Get timeline
            cursor.execute("""
                SELECT * FROM application_timeline
                WHERE application_id = ?
                ORDER BY changed_at DESC
            """, (app_id,))
            app["timeline"] = [dict(r) for r in cursor.fetchall()]

            return app

    def get_applications(
        self,
        status: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Dict], int]:
        """Get all applications with optional status filter"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            conditions = []
            params = []

            if status:
                conditions.append("a.status = ?")
                params.append(status)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            # Count
            cursor.execute(f"SELECT COUNT(*) FROM applications a {where_clause}", params)
            total = cursor.fetchone()[0]

            # Get applications
            cursor.execute(f"""
                SELECT a.*, j.title as job_title, j.url as job_url, j.source as job_source,
                       j.location as job_location, j.location_type as job_location_type,
                       c.name as company_name, c.logo_url as company_logo
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                LEFT JOIN companies c ON j.company_id = c.id
                {where_clause}
                ORDER BY a.last_updated DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])

            return [dict(r) for r in cursor.fetchall()], total

    def delete_application(self, app_id: str) -> bool:
        """Delete an application"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
            return cursor.rowcount > 0

    def get_applications_due_reminder(self) -> List[Dict]:
        """Get applications with reminders due today or overdue"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*, j.title as job_title, c.name as company_name
                FROM applications a
                JOIN jobs j ON a.job_id = j.id
                LEFT JOIN companies c ON j.company_id = c.id
                WHERE a.reminder_date <= date('now')
                  AND a.status NOT IN ('rejected', 'withdrawn', 'accepted')
                ORDER BY a.reminder_date
            """)
            return [dict(r) for r in cursor.fetchall()]

    # ============== Match Score Operations ==============

    def save_match_score(self, job_id: str, resume_hash: str, scores: Dict):
        """Save pre-calculated match score"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            score_id = f"score_{uuid.uuid4().hex[:12]}"

            cursor.execute("""
                INSERT OR REPLACE INTO job_match_scores (
                    id, job_id, resume_hash, overall_score, skills_score,
                    experience_score, education_score, matched_skills, missing_skills
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                score_id,
                job_id,
                resume_hash,
                scores["overall_score"],
                scores.get("skills_score"),
                scores.get("experience_score"),
                scores.get("education_score"),
                json.dumps(scores.get("matched_skills", [])),
                json.dumps(scores.get("missing_skills", []))
            ))

    def get_match_score(self, job_id: str, resume_hash: str) -> Optional[Dict]:
        """Get cached match score"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM job_match_scores
                WHERE job_id = ? AND resume_hash = ?
            """, (job_id, resume_hash))
            row = cursor.fetchone()

            if not row:
                return None

            score = dict(row)
            score["matched_skills"] = json.loads(score.get("matched_skills") or "[]")
            score["missing_skills"] = json.loads(score.get("missing_skills") or "[]")
            return score

    # ============== Cache Operations ==============

    def cache_search_results(self, query_hash: str, filters: Dict, job_ids: List[str], total: int, ttl_hours: int = 24):
        """Cache search results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cache_id = f"cache_{uuid.uuid4().hex[:12]}"
            expires_at = datetime.now().isoformat()  # Would add hours in real implementation

            cursor.execute("""
                INSERT OR REPLACE INTO search_cache (id, query_hash, filters_json, result_job_ids, total_results, expires_at)
                VALUES (?, ?, ?, ?, ?, datetime('now', '+' || ? || ' hours'))
            """, (
                cache_id,
                query_hash,
                json.dumps(filters),
                json.dumps(job_ids),
                total,
                ttl_hours
            ))

    def get_cached_search(self, query_hash: str) -> Optional[Dict]:
        """Get cached search results if not expired"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM search_cache
                WHERE query_hash = ? AND expires_at > datetime('now')
            """, (query_hash,))
            row = cursor.fetchone()

            if not row:
                return None

            cache = dict(row)
            cache["result_job_ids"] = json.loads(cache["result_job_ids"])
            cache["filters"] = json.loads(cache["filters_json"])
            return cache

    def clear_expired_cache(self):
        """Remove expired cache entries"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM search_cache WHERE expires_at < datetime('now')")
            return cursor.rowcount

    # ============== Saved Search Operations ==============

    def save_search(self, name: str, query: str, filters: Dict, notification_enabled: bool = False) -> str:
        """Save a search preset"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            search_id = f"search_{uuid.uuid4().hex[:12]}"
            cursor.execute("""
                INSERT INTO saved_searches (id, name, query, filters_json, notification_enabled)
                VALUES (?, ?, ?, ?, ?)
            """, (search_id, name, query, json.dumps(filters), notification_enabled))

            return search_id

    def get_saved_searches(self) -> List[Dict]:
        """Get all saved searches"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM saved_searches ORDER BY created_at DESC")

            searches = []
            for row in cursor.fetchall():
                search = dict(row)
                search["filters"] = json.loads(search["filters_json"])
                searches.append(search)

            return searches

    def delete_saved_search(self, search_id: str) -> bool:
        """Delete a saved search"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM saved_searches WHERE id = ?", (search_id,))
            return cursor.rowcount > 0

    # ============== Statistics ==============

    def get_job_stats(self) -> Dict:
        """Get job statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Total jobs
            cursor.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1")
            stats["total_jobs"] = cursor.fetchone()[0]

            # By source
            cursor.execute("""
                SELECT source, COUNT(*) as count
                FROM jobs WHERE is_active = 1
                GROUP BY source
            """)
            stats["by_source"] = {row[0]: row[1] for row in cursor.fetchall()}

            # By location type
            cursor.execute("""
                SELECT location_type, COUNT(*) as count
                FROM jobs WHERE is_active = 1 AND location_type IS NOT NULL
                GROUP BY location_type
            """)
            stats["by_location_type"] = {row[0]: row[1] for row in cursor.fetchall()}

            # Average salary
            cursor.execute("""
                SELECT AVG((COALESCE(salary_min, 0) + COALESCE(salary_max, 0)) / 2)
                FROM jobs
                WHERE is_active = 1 AND (salary_min IS NOT NULL OR salary_max IS NOT NULL)
            """)
            stats["average_salary"] = cursor.fetchone()[0]

            # Last scrape
            cursor.execute("SELECT MAX(scraped_at) FROM jobs")
            stats["last_scrape"] = cursor.fetchone()[0]

            return stats

    def get_application_stats(self) -> Dict:
        """Get application statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Total
            cursor.execute("SELECT COUNT(*) FROM applications")
            stats["total"] = cursor.fetchone()[0]

            # By status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM applications
                GROUP BY status
            """)
            stats["by_status"] = {row[0]: row[1] for row in cursor.fetchall()}

            # Response rate (% that moved past "applied")
            cursor.execute("""
                SELECT
                    COUNT(CASE WHEN status != 'applied' AND status != 'saved' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)
                FROM applications
                WHERE status != 'saved'
            """)
            stats["response_rate"] = cursor.fetchone()[0]

            return stats


# Singleton instance
_db_instance: Optional[JobDatabase] = None


def get_job_database() -> JobDatabase:
    """Get or create database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = JobDatabase()
    return _db_instance
