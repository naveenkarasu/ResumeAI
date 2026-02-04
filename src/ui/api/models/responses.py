"""Response models for API endpoints"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Citation(BaseModel):
    """Citation/source reference in response"""
    section: str
    text: str
    relevance_score: float = Field(ge=0, le=1)


class ChatResponse(BaseModel):
    """Response from chat endpoint"""
    response: str
    citations: list[Citation] = []
    mode: str
    grounding_score: Optional[float] = Field(None, ge=0, le=1)
    search_mode: Optional[str] = None
    processing_time_ms: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "response": "Based on your resume, you have experience with Python and JavaScript...",
                "citations": [
                    {"section": "Skills", "text": "Python, JavaScript, TypeScript", "relevance_score": 0.95}
                ],
                "mode": "chat",
                "grounding_score": 0.92,
                "search_mode": "hybrid+rerank"
            }
        }


class GapAnalysis(BaseModel):
    """Gap between resume and job requirements"""
    requirement: str
    status: str  # "met", "partial", "missing"
    suggestion: Optional[str] = None


class MatchResult(BaseModel):
    """Skill/experience match result"""
    item: str
    matched: bool
    resume_evidence: Optional[str] = None


class AnalysisResponse(BaseModel):
    """Response from job analysis endpoint"""
    match_score: float = Field(ge=0, le=100)
    matching_skills: list[MatchResult]
    gaps: list[GapAnalysis]
    keywords_to_add: list[str]
    suggestions: list[str]
    summary: str
    processing_time_ms: Optional[int] = None


class InterviewQuestion(BaseModel):
    """Interview question with metadata"""
    id: str
    question: str
    category: str
    role_types: list[str]
    difficulty: str
    tips: Optional[str] = None


class StarStory(BaseModel):
    """STAR-formatted story"""
    situation: str
    task: str
    action: str
    result: str
    question_fit: Optional[list[str]] = Field(
        None,
        description="Interview questions this story could answer"
    )


class PracticeFeedback(BaseModel):
    """Feedback on practice answer"""
    score: float = Field(ge=0, le=100)
    relevance_feedback: str
    structure_feedback: str
    specificity_feedback: str
    improvements: list[str]
    strengths: list[str]


class EmailResponse(BaseModel):
    """Generated email response"""
    subject: str
    body: str
    email_type: str
    variations: Optional[list[str]] = Field(
        None,
        description="Alternative versions of the email"
    )


class BackendInfo(BaseModel):
    """LLM backend information"""
    name: str
    status: str
    model: str
    is_active: bool = False


class SettingsResponse(BaseModel):
    """Current settings response"""
    backend: str
    available_backends: list[BackendInfo]
    use_hybrid_search: bool
    use_hyde: bool
    use_reranking: bool
    use_grounding: bool
    indexed_documents: int
    total_chunks: int


class StatusResponse(BaseModel):
    """System status response"""
    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    uptime_seconds: int
    rag_initialized: bool
    active_backend: str
    indexed_documents: int
    last_index_time: Optional[datetime] = None
    components: dict[str, str]


class ErrorResponse(BaseModel):
    """Error response format"""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid request",
                "detail": "Message cannot be empty",
                "error_code": "VALIDATION_ERROR"
            }
        }
