"""Interview Prep API router"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import logging

from ..dependencies import get_rag
from ..services.interview_service import InterviewService
from ..models.requests import StarStoryRequest, PracticeAnswerRequest
from ..models.responses import InterviewQuestion, StarStory, PracticeFeedback, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interview", tags=["interview"])

# Service instance
_interview_service: Optional[InterviewService] = None


def get_interview_service() -> InterviewService:
    """Get or create interview service instance"""
    global _interview_service
    if _interview_service is None:
        rag = get_rag()
        _interview_service = InterviewService(rag)
    return _interview_service


@router.get(
    "/questions",
    response_model=list[InterviewQuestion],
    summary="Get interview questions",
    description="Get filtered list of interview questions",
)
async def get_questions(
    category: Optional[str] = Query(None, description="Filter by category"),
    role_type: Optional[str] = Query(None, description="Filter by role type"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    limit: int = Query(10, ge=1, le=50, description="Max questions to return"),
    service: InterviewService = Depends(get_interview_service),
) -> list[InterviewQuestion]:
    """Get interview questions with optional filters"""
    return service.get_questions(
        category=category,
        role_type=role_type,
        difficulty=difficulty,
        limit=limit,
    )


@router.get(
    "/categories",
    response_model=list[dict],
    summary="Get question categories",
    description="Get list of available question categories",
)
async def get_categories(
    service: InterviewService = Depends(get_interview_service),
) -> list[dict]:
    """Get question categories"""
    return service.get_categories()


@router.get(
    "/roles",
    response_model=list[dict],
    summary="Get role types",
    description="Get list of available role types",
)
async def get_role_types(
    service: InterviewService = Depends(get_interview_service),
) -> list[dict]:
    """Get role types"""
    return service.get_role_types()


@router.post(
    "/star",
    response_model=StarStory,
    responses={500: {"model": ErrorResponse}},
    summary="Generate STAR story",
    description="Generate a STAR-formatted story from a situation or achievement",
)
async def generate_star(
    request: StarStoryRequest,
    service: InterviewService = Depends(get_interview_service),
) -> StarStory:
    """Generate a STAR story"""
    try:
        return await service.generate_star_story(
            situation=request.situation,
            question_context=request.question_context,
        )
    except Exception as e:
        logger.error(f"STAR generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/practice",
    response_model=PracticeFeedback,
    responses={500: {"model": ErrorResponse}},
    summary="Evaluate practice answer",
    description="Get AI feedback on a practice interview answer",
)
async def evaluate_practice(
    request: PracticeAnswerRequest,
    service: InterviewService = Depends(get_interview_service),
) -> PracticeFeedback:
    """Evaluate a practice answer"""
    try:
        return await service.evaluate_practice_answer(
            question_id=request.question_id,
            question_text=request.question_text,
            user_answer=request.user_answer,
        )
    except Exception as e:
        logger.error(f"Practice evaluation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/company/{company_name}",
    response_model=dict,
    summary="Research company",
    description="Get company research suggestions for interview prep",
)
async def research_company(
    company_name: str,
    service: InterviewService = Depends(get_interview_service),
) -> dict:
    """Research a company"""
    return await service.research_company(company_name)
