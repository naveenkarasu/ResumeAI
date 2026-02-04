# Job List Feature - System Architecture Design

**Version:** 1.0
**Date:** 2026-02-03
**Status:** Ready for Implementation

---

## 1. System Overview

### 1.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ JobListPage  │  │ JobSearchBar │  │ JobCard/     │  │ Application  │    │
│  │              │  │ (NLP Query)  │  │ Table/Split  │  │ Tracker      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│         │                 │                 │                 │             │
│  ┌──────┴─────────────────┴─────────────────┴─────────────────┴──────┐     │
│  │                    useJobList Hook (React Query)                   │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                     │                                        │
│  ┌──────────────────────────────────┴───────────────────────────────┐       │
│  │                      jobList.ts (API Client)                      │       │
│  └───────────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │ HTTP/REST
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (FastAPI)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────────┐     │
│  │                     /api/job-list/* Router                          │     │
│  │  POST /search  GET /jobs  GET /jobs/{id}  POST /apply  GET /track  │     │
│  └────────────────────────────────────────────────────────────────────┘     │
│                                     │                                        │
│  ┌──────────────────────────────────┴───────────────────────────────┐       │
│  │                      JobListService                               │       │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │       │
│  │  │ Job Search  │  │ Job Match   │  │ Application │               │       │
│  │  │ Engine      │  │ Calculator  │  │ Tracker     │               │       │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │       │
│  └───────────────────────────────────────────────────────────────────┘       │
│         │                    │                    │                          │
│  ┌──────┴────────┐   ┌──────┴────────┐   ┌──────┴────────┐                  │
│  │ ScraperService│   │ ResumeRAG     │   │ SQLite DB     │                  │
│  │ (Playwright)  │   │ (Existing)    │   │ (New)         │                  │
│  └───────────────┘   └───────────────┘   └───────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
                │                                      │
                ▼                                      ▼
┌───────────────────────────┐          ┌───────────────────────────────────────┐
│     External Job Sites    │          │            Data Storage               │
├───────────────────────────┤          ├───────────────────────────────────────┤
│ • LinkedIn                │          │ ┌─────────────┐  ┌─────────────────┐ │
│ • Indeed                  │          │ │ SQLite      │  │ ChromaDB        │ │
│ • Wellfound               │          │ │ jobs.db     │  │ (existing)      │ │
│ • Dice                    │          │ │ • jobs      │  │ • job_embeddings│ │
│ • Y Combinator            │          │ │ • companies │  │ • resume_embeds │ │
│ • Levels.fyi              │          │ │ • apps      │  └─────────────────┘ │
│ • BuiltIn                 │          │ │ • searches  │                      │
│ • Robert Half             │          │ └─────────────┘                      │
└───────────────────────────┘          └───────────────────────────────────────┘
```

### 1.2 Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        JOB SEARCH FLOW                                   │
└─────────────────────────────────────────────────────────────────────────┘

User Query: "remote ML engineer jobs $150k+ at startups"
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  1. QUERY PARSING (LLM)                                                  │
│     Input: Natural language query                                        │
│     Output: Structured filters                                           │
│     {                                                                    │
│       "keywords": ["ML engineer", "machine learning"],                   │
│       "location": "remote",                                              │
│       "salary_min": 150000,                                              │
│       "company_type": "startup"                                          │
│     }                                                                    │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  2. CACHE CHECK                                                          │
│     • Check if similar search exists in cache (< 24h old)                │
│     • If HIT: Return cached results                                      │
│     • If MISS: Proceed to scraping                                       │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  3. JOB SCRAPING (Playwright)                                            │
│     • Parallel scraping from multiple sites                              │
│     • Rate limiting: 1 req/5s per site                                   │
│     • Extract: title, company, location, salary, description             │
│     • Store raw jobs in SQLite                                           │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  4. EMBEDDING & MATCHING                                                 │
│     • Generate embeddings for job descriptions                           │
│     • Store in ChromaDB for semantic search                              │
│     • Calculate match score vs user's resume                             │
│     • Identify skills gaps                                               │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  5. RANKING & RESPONSE                                                   │
│     • Rank by: match_score * relevance * freshness                       │
│     • Return paginated results with metadata                             │
│     • Cache results for future queries                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Database Schema

### 2.1 SQLite Schema (jobs.db)

```sql
-- Jobs table: Scraped job listings
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,                    -- UUID
    url TEXT UNIQUE NOT NULL,               -- Source URL (deduplication key)
    title TEXT NOT NULL,
    company_id TEXT REFERENCES companies(id),
    location TEXT,
    location_type TEXT CHECK(location_type IN ('remote', 'hybrid', 'onsite')),
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT DEFAULT 'USD',
    description TEXT NOT NULL,
    requirements TEXT,                      -- JSON array of requirements
    posted_date DATE,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT NOT NULL,                   -- linkedin, indeed, etc.
    is_active BOOLEAN DEFAULT TRUE,
    embedding_id TEXT,                      -- Reference to ChromaDB

    -- Indexes for common queries
    INDEX idx_jobs_company (company_id),
    INDEX idx_jobs_location (location_type),
    INDEX idx_jobs_salary (salary_min, salary_max),
    INDEX idx_jobs_posted (posted_date DESC),
    INDEX idx_jobs_source (source)
);

-- Companies table: Company metadata
CREATE TABLE companies (
    id TEXT PRIMARY KEY,                    -- UUID
    name TEXT NOT NULL,
    normalized_name TEXT UNIQUE NOT NULL,   -- Lowercase, no spaces (dedup)
    logo_url TEXT,
    website TEXT,
    industry TEXT,
    size TEXT CHECK(size IN ('startup', 'small', 'medium', 'large', 'enterprise')),
    rating REAL,                            -- Glassdoor/Indeed rating

    INDEX idx_companies_name (normalized_name)
);

-- Applications table: User's application tracking
CREATE TABLE applications (
    id TEXT PRIMARY KEY,                    -- UUID
    job_id TEXT REFERENCES jobs(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK(status IN (
        'saved', 'applied', 'screening', 'interview',
        'offer', 'rejected', 'withdrawn', 'accepted'
    )),
    applied_date DATE,
    notes TEXT,
    resume_version TEXT,                    -- Which resume was used
    cover_letter TEXT,
    reminder_date DATE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(job_id),                         -- One application per job
    INDEX idx_applications_status (status),
    INDEX idx_applications_reminder (reminder_date)
);

-- Application timeline: Status change history
CREATE TABLE application_timeline (
    id TEXT PRIMARY KEY,
    application_id TEXT REFERENCES applications(id) ON DELETE CASCADE,
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,

    INDEX idx_timeline_app (application_id)
);

-- Saved searches: User's search presets
CREATE TABLE saved_searches (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    query TEXT,                             -- Original NL query
    filters_json TEXT NOT NULL,             -- Structured filters
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_run_at TIMESTAMP,
    notification_enabled BOOLEAN DEFAULT FALSE,

    INDEX idx_searches_name (name)
);

-- Search cache: Recent search results
CREATE TABLE search_cache (
    id TEXT PRIMARY KEY,
    query_hash TEXT UNIQUE NOT NULL,        -- Hash of normalized query
    filters_json TEXT NOT NULL,
    result_job_ids TEXT NOT NULL,           -- JSON array of job IDs
    total_results INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,

    INDEX idx_cache_hash (query_hash),
    INDEX idx_cache_expires (expires_at)
);

-- Job match scores: Pre-calculated match scores
CREATE TABLE job_match_scores (
    id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES jobs(id) ON DELETE CASCADE,
    resume_hash TEXT NOT NULL,              -- Hash of resume content
    overall_score REAL NOT NULL,
    skills_score REAL,
    experience_score REAL,
    education_score REAL,
    matched_skills TEXT,                    -- JSON array
    missing_skills TEXT,                    -- JSON array
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(job_id, resume_hash),
    INDEX idx_match_job (job_id),
    INDEX idx_match_score (overall_score DESC)
);
```

### 2.2 ChromaDB Collections

```python
# New collection for job embeddings
job_embeddings = {
    "collection_name": "job_descriptions",
    "embedding_function": "all-MiniLM-L6-v2",  # Same as resume
    "metadata": {
        "job_id": str,           # Reference to SQLite
        "title": str,
        "company": str,
        "location_type": str,
        "posted_date": str,
        "source": str
    }
}
```

---

## 3. API Specification

### 3.1 Endpoints

```yaml
openapi: 3.0.3
info:
  title: Job List API
  version: 1.0.0

paths:
  /api/job-list/search:
    post:
      summary: Search for jobs
      description: Natural language or structured job search
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/JobSearchRequest'
      responses:
        200:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/JobSearchResponse'

  /api/job-list/jobs:
    get:
      summary: Get cached jobs
      parameters:
        - name: page
          in: query
          schema: { type: integer, default: 1 }
        - name: limit
          in: query
          schema: { type: integer, default: 20, max: 100 }
        - name: sort_by
          in: query
          schema: { type: string, enum: [match_score, posted_date, salary] }
        - name: filters
          in: query
          schema: { type: string, description: "JSON encoded filters" }

  /api/job-list/jobs/{job_id}:
    get:
      summary: Get job details with match analysis

  /api/job-list/jobs/{job_id}/apply:
    post:
      summary: Generate application materials
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                generate_cover_letter: { type: boolean }
                custom_prompt: { type: string }

  /api/job-list/applications:
    get:
      summary: Get all tracked applications
    post:
      summary: Track a new application

  /api/job-list/applications/{app_id}:
    put:
      summary: Update application status
    delete:
      summary: Remove application tracking

  /api/job-list/recommendations:
    get:
      summary: Get AI-recommended jobs based on resume

  /api/job-list/scrape/status:
    get:
      summary: Get scraping job status

  /api/job-list/saved-searches:
    get:
      summary: List saved searches
    post:
      summary: Save a search preset

components:
  schemas:
    JobSearchRequest:
      type: object
      properties:
        query:
          type: string
          description: Natural language search query
          example: "remote ML engineer jobs $150k+ at startups"
        filters:
          $ref: '#/components/schemas/JobFilters'
        include_match_scores:
          type: boolean
          default: true
        page:
          type: integer
          default: 1
        limit:
          type: integer
          default: 20

    JobFilters:
      type: object
      properties:
        keywords:
          type: array
          items: { type: string }
        location:
          type: string
        location_type:
          type: array
          items: { type: string, enum: [remote, hybrid, onsite] }
        salary_min:
          type: integer
        salary_max:
          type: integer
        company_size:
          type: array
          items: { type: string, enum: [startup, small, medium, large, enterprise] }
        sources:
          type: array
          items: { type: string }
        posted_within_days:
          type: integer
          default: 30

    JobSearchResponse:
      type: object
      properties:
        jobs:
          type: array
          items:
            $ref: '#/components/schemas/JobListing'
        total:
          type: integer
        page:
          type: integer
        pages:
          type: integer
        search_id:
          type: string
        cached:
          type: boolean
        scrape_status:
          type: string
          enum: [completed, in_progress, queued]

    JobListing:
      type: object
      properties:
        id:
          type: string
        title:
          type: string
        company:
          $ref: '#/components/schemas/Company'
        location:
          type: string
        location_type:
          type: string
        salary_range:
          type: string
        posted_date:
          type: string
          format: date
        source:
          type: string
        url:
          type: string
        match_score:
          type: number
          minimum: 0
          maximum: 100
        match_quality:
          type: string
          enum: [excellent, good, fair, poor]
        matched_skills:
          type: array
          items: { type: string }
        missing_skills:
          type: array
          items: { type: string }
        application_status:
          type: string
          nullable: true

    Company:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
        logo_url:
          type: string
        industry:
          type: string
        size:
          type: string
        rating:
          type: number

    Application:
      type: object
      properties:
        id:
          type: string
        job:
          $ref: '#/components/schemas/JobListing'
        status:
          type: string
          enum: [saved, applied, screening, interview, offer, rejected, withdrawn, accepted]
        applied_date:
          type: string
          format: date
        notes:
          type: string
        reminder_date:
          type: string
          format: date
        timeline:
          type: array
          items:
            type: object
            properties:
              status: { type: string }
              date: { type: string }
              notes: { type: string }
```

---

## 4. Component Design

### 4.1 Backend Services

```
src/ui/api/
├── models/
│   └── job_list_models.py      # Pydantic models
├── services/
│   ├── job_list_service.py     # Main service orchestrator
│   ├── job_scraper_service.py  # Playwright scraping
│   └── job_search_service.py   # Search & ranking
├── routers/
│   └── job_list.py             # API endpoints
└── scrapers/
    ├── base_scraper.py         # Abstract base class
    ├── linkedin_scraper.py
    ├── indeed_scraper.py
    ├── wellfound_scraper.py
    ├── dice_scraper.py
    ├── ycombinator_scraper.py
    ├── levelsfyi_scraper.py
    ├── builtin_scraper.py
    └── roberthalf_scraper.py
```

### 4.2 Frontend Components

```
frontend/src/
├── api/
│   └── jobList.ts              # API client
├── hooks/
│   └── useJobList.ts           # React Query hooks
├── pages/
│   └── JobListPage.tsx         # Main page
├── components/
│   └── job-list/
│       ├── JobSearchBar.tsx    # NLP search input
│       ├── JobFilters.tsx      # Filter sidebar
│       ├── JobCard.tsx         # Card view item
│       ├── JobTable.tsx        # Table view
│       ├── JobSplitView.tsx    # Split list/detail
│       ├── JobDetail.tsx       # Full job detail
│       ├── MatchScoreBadge.tsx # Score visualization
│       ├── SkillsGapChart.tsx  # Missing skills
│       ├── ApplicationForm.tsx # Track application
│       ├── ApplicationKanban.tsx # Pipeline view
│       └── ViewToggle.tsx      # View mode switch
└── types/
    └── jobList.ts              # TypeScript types
```

---

## 5. Scraper Architecture

### 5.1 Base Scraper Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, AsyncGenerator
from playwright.async_api import Page

@dataclass
class ScrapedJob:
    url: str
    title: str
    company_name: str
    location: Optional[str]
    location_type: Optional[str]  # remote/hybrid/onsite
    salary_text: Optional[str]
    description: str
    requirements: List[str]
    posted_date: Optional[str]
    source: str

class BaseScraper(ABC):
    """Abstract base class for job site scrapers"""

    RATE_LIMIT_SECONDS = 5  # Min seconds between requests
    MAX_PAGES = 10          # Max pages to scrape per search

    def __init__(self, page: Page):
        self.page = page
        self.last_request_time = 0

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the source identifier (e.g., 'linkedin')"""
        pass

    @abstractmethod
    async def search(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        filters: Optional[dict] = None
    ) -> AsyncGenerator[ScrapedJob, None]:
        """Search for jobs and yield results"""
        pass

    @abstractmethod
    async def get_job_details(self, url: str) -> ScrapedJob:
        """Get full details for a specific job"""
        pass

    async def _rate_limit(self):
        """Enforce rate limiting between requests"""
        import asyncio
        import time
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_SECONDS:
            await asyncio.sleep(self.RATE_LIMIT_SECONDS - elapsed)
        self.last_request_time = time.time()

    async def _random_delay(self, min_sec=1, max_sec=3):
        """Add random delay to appear more human"""
        import asyncio
        import random
        await asyncio.sleep(random.uniform(min_sec, max_sec))
```

### 5.2 Scraper Registry

```python
SCRAPERS = {
    "linkedin": LinkedInScraper,
    "indeed": IndeedScraper,
    "wellfound": WellfoundScraper,
    "dice": DiceScraper,
    "ycombinator": YCombinatorScraper,
    "levelsfyi": LevelsFyiScraper,
    "builtin": BuiltInScraper,
    "roberthalf": RobertHalfScraper,
}
```

---

## 6. AI Integration

### 6.1 Query Parser (NLP to Structured)

```python
QUERY_PARSER_PROMPT = """
Parse the following job search query into structured filters.

Query: "{query}"

Extract and return JSON with these fields:
- keywords: List of job-related keywords/titles
- location: Location string or "remote"
- location_type: "remote", "hybrid", "onsite", or null
- salary_min: Minimum salary as integer, or null
- salary_max: Maximum salary as integer, or null
- company_type: "startup", "enterprise", etc., or null
- experience_level: "entry", "mid", "senior", "lead", or null
- industry: Industry/domain if mentioned, or null

Return ONLY valid JSON, no explanation.
"""
```

### 6.2 Cover Letter Generator

```python
COVER_LETTER_PROMPT = """
Write a compelling cover letter for this job application.

JOB DETAILS:
Title: {job_title}
Company: {company}
Description: {job_description}

CANDIDATE RESUME:
{resume_context}

MATCHED SKILLS: {matched_skills}
MISSING SKILLS: {missing_skills}

Guidelines:
1. Keep it under 300 words
2. Lead with strongest matching qualifications
3. Address 1-2 missing skills with transferable experience
4. Show genuine interest in the company
5. End with clear call to action

Write the cover letter now:
"""
```

---

## 7. File Structure Summary

```
src/
├── ui/api/
│   ├── models/
│   │   └── job_list_models.py          # NEW: Pydantic models
│   ├── services/
│   │   ├── job_list_service.py         # NEW: Main orchestrator
│   │   ├── job_scraper_service.py      # NEW: Scraping coordinator
│   │   └── job_search_service.py       # NEW: Search & matching
│   ├── routers/
│   │   └── job_list.py                 # NEW: API endpoints
│   └── scrapers/                       # NEW: Scraper modules
│       ├── __init__.py
│       ├── base_scraper.py
│       ├── linkedin_scraper.py
│       ├── indeed_scraper.py
│       ├── wellfound_scraper.py
│       ├── dice_scraper.py
│       ├── ycombinator_scraper.py
│       ├── levelsfyi_scraper.py
│       ├── builtin_scraper.py
│       └── roberthalf_scraper.py
├── data/
│   └── jobs.db                         # NEW: SQLite database

frontend/src/
├── api/
│   └── jobList.ts                      # NEW: API client
├── hooks/
│   └── useJobList.ts                   # NEW: React hooks
├── pages/
│   └── JobListPage.tsx                 # NEW: Main page
├── components/
│   └── job-list/                       # NEW: Component directory
│       ├── index.ts
│       ├── JobSearchBar.tsx
│       ├── JobFilters.tsx
│       ├── JobCard.tsx
│       ├── JobTable.tsx
│       ├── JobSplitView.tsx
│       ├── JobDetail.tsx
│       ├── MatchScoreBadge.tsx
│       ├── SkillsGapChart.tsx
│       ├── ApplicationForm.tsx
│       ├── ApplicationKanban.tsx
│       └── ViewToggle.tsx
└── types/
    └── jobList.ts                      # NEW: TypeScript types
```

---

## 8. Implementation Phases

### Phase 1: Core Infrastructure (MVP)
1. SQLite database setup with schema
2. Base scraper framework
3. 2-3 initial scrapers (Indeed, Y Combinator, BuiltIn - easiest)
4. Basic API endpoints (search, list, details)
5. Simple frontend with card view

### Phase 2: AI Integration
1. Query parser (NLP → structured)
2. Job-resume matching with scores
3. Skills gap analysis
4. AI recommendations endpoint

### Phase 3: Full Scraper Suite
1. LinkedIn scraper (hardest - anti-bot)
2. Remaining scrapers (Dice, Wellfound, Levels.fyi, Robert Half)
3. Parallel scraping orchestration
4. Cache management

### Phase 4: Application Tracking
1. Application status tracking
2. Kanban board view
3. Reminders system
4. Cover letter generation

### Phase 5: Polish & Views
1. Table view
2. Split view
3. Saved searches
4. Notifications (optional)

---

## 9. Security Considerations

1. **Rate Limiting**: Conservative scraping to avoid IP bans
2. **robots.txt**: Respect site policies
3. **No Credential Storage**: Never store job site login credentials
4. **Data Retention**: Auto-expire old job data (30 days)
5. **User Data**: Application notes stored locally only

---

**Design Status: APPROVED FOR IMPLEMENTATION**

Proceed with `/sc:implement` to begin Phase 1.
