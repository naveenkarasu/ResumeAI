"""Pydantic models for Job List feature"""

from datetime import date, datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class LocationType(str, Enum):
    """Job location type"""
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class CompanySize(str, Enum):
    """Company size categories"""
    STARTUP = "startup"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"


class ApplicationStatus(str, Enum):
    """Application tracking status"""
    SAVED = "saved"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    ACCEPTED = "accepted"


class MatchQuality(str, Enum):
    """Match quality rating"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class JobSource(str, Enum):
    """Supported job sources"""
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    WELLFOUND = "wellfound"
    DICE = "dice"
    YCOMBINATOR = "ycombinator"
    LEVELSFYI = "levelsfyi"
    BUILTIN = "builtin"
    ROBERTHALF = "roberthalf"
    # New scraper sources
    GITHUB = "github"
    SIMPLIFY = "simplify"
    JOBRIGHT = "jobright"
    REMOTEOK = "remoteok"
    HACKERNEWS = "hackernews"
    WEWORKREMOTELY = "weworkremotely"
    GOOGLE_DORK = "google_dork"


# ============== Company Models ==============

class Company(BaseModel):
    """Company information"""
    id: str
    name: str
    logo_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[CompanySize] = None
    rating: Optional[float] = Field(None, ge=0, le=5)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "company_123",
                "name": "TechCorp Inc",
                "logo_url": "https://example.com/logo.png",
                "industry": "Technology",
                "size": "startup",
                "rating": 4.5
            }
        }


class CompanyCreate(BaseModel):
    """Create company request"""
    name: str
    logo_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[CompanySize] = None
    rating: Optional[float] = Field(None, ge=0, le=5)


# ============== Job Listing Models ==============

class JobListing(BaseModel):
    """Job listing with match information"""
    id: str
    url: str
    title: str
    company: Company
    location: Optional[str] = None
    location_type: Optional[LocationType] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "USD"
    salary_text: Optional[str] = None  # Original salary string
    description: str
    requirements: List[str] = Field(default_factory=list)
    posted_date: Optional[date] = None
    scraped_at: datetime
    source: JobSource
    is_active: bool = True

    # Match information (populated when comparing to resume)
    match_score: Optional[float] = Field(None, ge=0, le=100)
    match_quality: Optional[MatchQuality] = None
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)

    # Application status (if tracked)
    application_status: Optional[ApplicationStatus] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "job_abc123",
                "url": "https://indeed.com/job/123",
                "title": "Senior Software Engineer",
                "company": {
                    "id": "company_123",
                    "name": "TechCorp Inc",
                    "size": "startup"
                },
                "location": "San Francisco, CA",
                "location_type": "hybrid",
                "salary_min": 150000,
                "salary_max": 200000,
                "description": "We are looking for...",
                "requirements": ["Python", "AWS", "5+ years experience"],
                "posted_date": "2026-02-01",
                "source": "indeed",
                "match_score": 85.5,
                "match_quality": "excellent",
                "matched_skills": ["Python", "AWS"],
                "missing_skills": ["Kubernetes"]
            }
        }


class JobListingBrief(BaseModel):
    """Brief job listing for list views"""
    id: str
    title: str
    company_name: str
    company_logo: Optional[str] = None
    location: Optional[str] = None
    location_type: Optional[LocationType] = None
    salary_text: Optional[str] = None
    posted_date: Optional[date] = None
    source: JobSource
    match_score: Optional[float] = None
    match_quality: Optional[MatchQuality] = None
    application_status: Optional[ApplicationStatus] = None


# ============== Search & Filter Models ==============

class JobFilters(BaseModel):
    """Structured job search filters"""
    keywords: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    location_type: List[LocationType] = Field(default_factory=list)
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    company_size: List[CompanySize] = Field(default_factory=list)
    sources: List[JobSource] = Field(default_factory=list)
    posted_within_days: int = Field(default=30, ge=1, le=365)
    experience_level: Optional[str] = None  # entry, mid, senior, lead
    industry: Optional[str] = None
    # Google dorking parameters
    dork_id: Optional[str] = None  # Specific dork query ID
    dork_category: Optional[str] = None  # Category of dorks to use

    @field_validator("salary_max")
    @classmethod
    def validate_salary_range(cls, v, info):
        if v is not None and info.data.get("salary_min") is not None:
            if v < info.data["salary_min"]:
                raise ValueError("salary_max must be >= salary_min")
        return v


class JobSearchRequest(BaseModel):
    """Job search request with NLP query support"""
    query: Optional[str] = Field(
        None,
        description="Natural language search query",
        min_length=3,
        max_length=500
    )
    filters: Optional[JobFilters] = None
    include_match_scores: bool = True
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="match_score", pattern="^(match_score|posted_date|salary)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")

    @field_validator("query", "filters")
    @classmethod
    def require_query_or_filters(cls, v, info):
        # At least one of query or filters must be provided
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "query": "remote ML engineer jobs $150k+ at startups",
                "filters": {
                    "location_type": ["remote"],
                    "salary_min": 150000
                },
                "include_match_scores": True,
                "page": 1,
                "limit": 20
            }
        }


class ScrapeStatus(str, Enum):
    """Scraping job status"""
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    QUEUED = "queued"
    FAILED = "failed"


class JobSearchResponse(BaseModel):
    """Job search response with pagination"""
    jobs: List[JobListingBrief]
    total: int
    page: int
    pages: int
    limit: int
    search_id: Optional[str] = None
    cached: bool = False
    scrape_status: ScrapeStatus = ScrapeStatus.COMPLETED
    filters_applied: Optional[JobFilters] = None

    class Config:
        json_schema_extra = {
            "example": {
                "jobs": [],
                "total": 150,
                "page": 1,
                "pages": 8,
                "limit": 20,
                "search_id": "search_xyz",
                "cached": True,
                "scrape_status": "completed"
            }
        }


# ============== Application Tracking Models ==============

class ApplicationTimelineEntry(BaseModel):
    """Single entry in application timeline"""
    old_status: Optional[ApplicationStatus] = None
    new_status: ApplicationStatus
    changed_at: datetime
    notes: Optional[str] = None


class Application(BaseModel):
    """Application tracking record"""
    id: str
    job: JobListingBrief
    status: ApplicationStatus
    applied_date: Optional[date] = None
    notes: Optional[str] = None
    resume_version: Optional[str] = None
    cover_letter: Optional[str] = None
    reminder_date: Optional[date] = None
    last_updated: datetime
    timeline: List[ApplicationTimelineEntry] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "app_123",
                "job": {"id": "job_abc", "title": "Senior Engineer"},
                "status": "interview",
                "applied_date": "2026-02-01",
                "notes": "Had phone screen, waiting for onsite",
                "reminder_date": "2026-02-10"
            }
        }


class ApplicationCreate(BaseModel):
    """Create application tracking request"""
    job_id: str
    status: ApplicationStatus = ApplicationStatus.SAVED
    notes: Optional[str] = None
    resume_version: Optional[str] = None
    reminder_date: Optional[date] = None


class ApplicationUpdate(BaseModel):
    """Update application request"""
    status: Optional[ApplicationStatus] = None
    notes: Optional[str] = None
    cover_letter: Optional[str] = None
    reminder_date: Optional[date] = None


class ApplicationListResponse(BaseModel):
    """List of applications"""
    applications: List[Application]
    total: int
    by_status: dict[str, int] = Field(default_factory=dict)


# ============== Saved Search Models ==============

class SavedSearch(BaseModel):
    """Saved search preset"""
    id: str
    name: str
    query: Optional[str] = None
    filters: JobFilters
    created_at: datetime
    last_run_at: Optional[datetime] = None
    notification_enabled: bool = False
    result_count: Optional[int] = None


class SavedSearchCreate(BaseModel):
    """Create saved search request"""
    name: str = Field(..., min_length=1, max_length=100)
    query: Optional[str] = None
    filters: Optional[JobFilters] = None
    notification_enabled: bool = False


# ============== AI Features Models ==============

class QueryParseResult(BaseModel):
    """Result of parsing natural language query"""
    original_query: str
    filters: JobFilters
    confidence: float = Field(ge=0, le=1)
    interpretation: str  # Human-readable interpretation


class JobRecommendation(BaseModel):
    """AI-recommended job"""
    job: JobListingBrief
    recommendation_reason: str
    relevance_score: float = Field(ge=0, le=100)


class CoverLetterRequest(BaseModel):
    """Request to generate cover letter"""
    job_id: str
    custom_prompt: Optional[str] = None
    tone: str = Field(default="professional", pattern="^(professional|casual|enthusiastic)$")
    max_words: int = Field(default=300, ge=100, le=500)


class CoverLetterResponse(BaseModel):
    """Generated cover letter"""
    job_id: str
    cover_letter: str
    word_count: int
    highlights_used: List[str]  # Resume points emphasized


# ============== Statistics Models ==============

class JobSearchStats(BaseModel):
    """Search statistics"""
    total_jobs_indexed: int
    jobs_by_source: dict[str, int]
    jobs_by_location_type: dict[str, int]
    average_salary: Optional[float] = None
    last_scrape_at: Optional[datetime] = None


class ApplicationStats(BaseModel):
    """Application tracking statistics"""
    total_applications: int
    by_status: dict[str, int]
    response_rate: Optional[float] = None  # % that got past "applied"
    average_time_to_response: Optional[int] = None  # days
    top_matched_skills: List[str] = Field(default_factory=list)
    top_missing_skills: List[str] = Field(default_factory=list)
