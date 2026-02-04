"""Request models for API endpoints"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class ChatRequest(BaseModel):
    """Request for chat endpoint"""
    message: str = Field(..., min_length=1, max_length=5000)
    mode: Literal["chat", "email", "tailor", "interview"] = "chat"
    job_description: Optional[str] = Field(None, max_length=10000)
    use_verification: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What programming languages do I know?",
                "mode": "chat",
                "use_verification": False
            }
        }


class AnalyzeJobRequest(BaseModel):
    """Request for job analysis"""
    job_description: str = Field(..., min_length=50, max_length=15000)
    focus_areas: list[str] = Field(
        default=["skills", "experience", "keywords"],
        description="Areas to focus the analysis on"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "job_description": "Senior Software Engineer at Tech Corp...",
                "focus_areas": ["skills", "experience", "keywords"]
            }
        }


class InterviewQuestionRequest(BaseModel):
    """Request for interview questions"""
    category: Optional[str] = Field(None, description="Question category filter")
    role_type: Optional[str] = Field(None, description="Target role type")
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    limit: int = Field(default=10, ge=1, le=50)


class StarStoryRequest(BaseModel):
    """Request for STAR story generation"""
    situation: str = Field(..., min_length=10, max_length=2000)
    question_context: Optional[str] = Field(
        None,
        description="Interview question this story should answer"
    )


class PracticeAnswerRequest(BaseModel):
    """Request for practice answer feedback"""
    question_id: str
    question_text: str
    user_answer: str = Field(..., min_length=10, max_length=5000)


class EmailTone(str, Enum):
    professional = "professional"
    conversational = "conversational"
    enthusiastic = "enthusiastic"


class EmailLength(str, Enum):
    brief = "brief"
    standard = "standard"
    detailed = "detailed"


class EmailType(str, Enum):
    application = "application"
    followup = "followup"
    thankyou = "thankyou"


class EmailRequest(BaseModel):
    """Request for email generation"""
    email_type: EmailType = EmailType.application
    job_description: str = Field(..., min_length=50, max_length=10000)
    company_name: Optional[str] = None
    recipient_name: Optional[str] = None
    tone: EmailTone = EmailTone.professional
    length: EmailLength = EmailLength.standard
    focus: Optional[Literal["technical", "leadership", "culture"]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email_type": "application",
                "job_description": "Software Engineer position...",
                "company_name": "Tech Corp",
                "tone": "professional",
                "length": "standard"
            }
        }


class SettingsUpdateRequest(BaseModel):
    """Request to update settings"""
    backend: Optional[str] = Field(None, description="LLM backend to use")
    use_hybrid_search: Optional[bool] = None
    use_hyde: Optional[bool] = None
    use_reranking: Optional[bool] = None
    use_grounding: Optional[bool] = None
