"""Job Matching Data Models"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class SkillImportance(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    NICE_TO_HAVE = "nice-to-have"


class MatchQuality(str, Enum):
    EXCELLENT = "excellent"    # 85-100%
    GOOD = "good"              # 70-84%
    FAIR = "fair"              # 50-69%
    POOR = "poor"              # Below 50%


# === Request Models ===

class JobMatchRequest(BaseModel):
    """Request to match resume against a job description"""
    job_description: str = Field(..., min_length=50, description="Full job description text")
    job_title: Optional[str] = Field(None, description="Position title")
    company: Optional[str] = Field(None, description="Company name")
    job_url: Optional[str] = Field(None, description="Source URL of job posting")
    resume_id: Optional[str] = Field(None, description="Specific resume to use (for multi-resume)")

    class Config:
        json_schema_extra = {
            "example": {
                "job_description": "We are looking for a Senior Software Engineer with 5+ years of experience in Python, FastAPI, and React...",
                "job_title": "Senior Software Engineer",
                "company": "TechCorp",
                "job_url": "https://example.com/jobs/123"
            }
        }


class BatchJobMatchRequest(BaseModel):
    """Request to match resume against multiple jobs"""
    jobs: List[JobMatchRequest] = Field(..., min_length=1, max_length=10)


class JobOptimizeRequest(BaseModel):
    """Request for resume optimization suggestions for a job"""
    job_description: str = Field(..., min_length=50)
    focus_areas: Optional[List[str]] = Field(None, description="Specific areas to focus on")


# === Response Models ===

class MatchedSkill(BaseModel):
    """A skill that matched between resume and job"""
    skill: str = Field(..., description="The matched skill")
    source: str = Field(..., description="Where found in resume")
    relevance: float = Field(..., ge=0, le=1, description="Relevance score 0-1")
    context: Optional[str] = Field(None, description="Context from resume")


class MissingSkill(BaseModel):
    """A skill required by job but not found in resume"""
    skill: str = Field(..., description="The missing skill")
    importance: SkillImportance = Field(..., description="How important this skill is")
    suggestion: str = Field(..., description="How to address this gap")
    related_skills: Optional[List[str]] = Field(None, description="Related skills you have")


class Recommendation(BaseModel):
    """An actionable recommendation to improve match"""
    title: str = Field(..., description="Short recommendation title")
    description: str = Field(..., description="Detailed recommendation")
    priority: int = Field(..., ge=1, le=5, description="Priority 1-5 (1=highest)")
    category: str = Field(..., description="Category: skills, experience, keywords, format")


class ScoreBreakdown(BaseModel):
    """Detailed breakdown of match scores by category"""
    skills_match: float = Field(..., ge=0, le=100, description="Technical skills alignment %")
    experience_match: float = Field(..., ge=0, le=100, description="Experience level match %")
    education_match: float = Field(..., ge=0, le=100, description="Education requirements match %")
    keywords_match: float = Field(..., ge=0, le=100, description="ATS keyword coverage %")

    @property
    def weighted_average(self) -> float:
        """Calculate weighted average score"""
        weights = {
            "skills_match": 0.40,
            "experience_match": 0.25,
            "education_match": 0.15,
            "keywords_match": 0.20
        }
        return sum(getattr(self, k) * v for k, v in weights.items())


class ExtractedRequirements(BaseModel):
    """Requirements extracted from job description"""
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    experience_years: Optional[int] = Field(None)
    experience_level: Optional[str] = Field(None)  # junior, mid, senior, lead
    education: Optional[str] = Field(None)
    keywords: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)


class JobMatchResponse(BaseModel):
    """Complete response for a job match analysis"""
    match_id: str = Field(..., description="Unique ID for this match")
    overall_score: float = Field(..., ge=0, le=100, description="Overall match percentage")
    quality: MatchQuality = Field(..., description="Match quality category")

    # Score breakdown
    scores: ScoreBreakdown = Field(..., description="Detailed score breakdown")

    # Extracted info
    requirements: ExtractedRequirements = Field(..., description="Extracted job requirements")

    # Detailed matching
    matched_skills: List[MatchedSkill] = Field(default_factory=list)
    missing_skills: List[MissingSkill] = Field(default_factory=list)

    # Recommendations
    recommendations: List[Recommendation] = Field(default_factory=list)

    # Metadata
    job_title: Optional[str] = Field(None)
    company: Optional[str] = Field(None)
    job_url: Optional[str] = Field(None)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    # Resume info
    resume_used: Optional[str] = Field(None, description="Which resume was analyzed")

    class Config:
        json_schema_extra = {
            "example": {
                "match_id": "match_abc123",
                "overall_score": 78.5,
                "quality": "good",
                "scores": {
                    "skills_match": 82.0,
                    "experience_match": 90.0,
                    "education_match": 100.0,
                    "keywords_match": 65.0
                },
                "matched_skills": [
                    {"skill": "Python", "source": "Skills section", "relevance": 0.95}
                ],
                "missing_skills": [
                    {"skill": "Kubernetes", "importance": "required", "suggestion": "Highlight container experience"}
                ]
            }
        }


class BatchJobMatchResponse(BaseModel):
    """Response for batch job matching"""
    results: List[JobMatchResponse] = Field(default_factory=list)
    total_jobs: int
    average_score: float
    best_match: Optional[JobMatchResponse] = None


class JobHistoryItem(BaseModel):
    """A saved job match for history tracking"""
    match_id: str
    job_title: Optional[str]
    company: Optional[str]
    overall_score: float
    quality: MatchQuality
    analyzed_at: datetime
    job_url: Optional[str] = None
    notes: Optional[str] = None
    status: str = "analyzed"  # analyzed, applied, interviewing, rejected, offered


class JobHistoryResponse(BaseModel):
    """Response containing job match history"""
    items: List[JobHistoryItem] = Field(default_factory=list)
    total_count: int
    average_score: float
    best_score: float
    worst_score: float


class SkillFrequency(BaseModel):
    """Frequency of a skill across job matches"""
    skill: str
    times_required: int
    times_matched: int
    match_rate: float  # percentage


class SkillsAnalytics(BaseModel):
    """Analytics about skills across all job matches"""
    strongest_skills: List[SkillFrequency] = Field(default_factory=list)
    weakest_skills: List[SkillFrequency] = Field(default_factory=list)
    most_requested: List[SkillFrequency] = Field(default_factory=list)
    improvement_areas: List[str] = Field(default_factory=list)
