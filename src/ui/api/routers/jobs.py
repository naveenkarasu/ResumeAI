"""Job Matching API router"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
import logging

from ..dependencies import get_rag
from ..services.job_service import JobMatchingService
from ..models.job_models import (
    JobMatchRequest,
    JobMatchResponse,
    BatchJobMatchRequest,
    BatchJobMatchResponse,
    JobHistoryResponse,
    SkillsAnalytics,
)
from ..models.responses import ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# Service instance
_job_service: Optional[JobMatchingService] = None


def get_job_service() -> JobMatchingService:
    """Get or create job matching service instance"""
    global _job_service
    if _job_service is None:
        rag = get_rag()
        _job_service = JobMatchingService(rag)
    return _job_service


@router.post(
    "/match",
    response_model=JobMatchResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid job description"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Match resume against job description",
    description="""
    Analyze how well your resume matches a job description.

    Returns:
    - Overall match score (0-100%)
    - Score breakdown by category (skills, experience, education, keywords)
    - Matched skills with evidence from resume
    - Missing skills with suggestions
    - Actionable recommendations to improve your match
    """,
)
async def match_job(
    request: JobMatchRequest,
    service: JobMatchingService = Depends(get_job_service),
) -> JobMatchResponse:
    """Match resume against a job description"""
    try:
        result = await service.match(request)
        return result
    except ValueError as e:
        logger.warning(f"Invalid job match request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Job matching error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/batch",
    response_model=BatchJobMatchResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Match resume against multiple jobs",
    description="""
    Analyze your resume against multiple job descriptions at once.

    Useful for:
    - Comparing opportunities
    - Finding best-fit roles
    - Prioritizing applications

    Returns results for each job plus aggregate statistics.
    """,
)
async def batch_match_jobs(
    request: BatchJobMatchRequest,
    service: JobMatchingService = Depends(get_job_service),
) -> BatchJobMatchResponse:
    """Match resume against multiple job descriptions"""
    try:
        result = await service.batch_match(request.jobs)
        return result
    except ValueError as e:
        logger.warning(f"Invalid batch match request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Batch matching error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/history",
    response_model=JobHistoryResponse,
    summary="Get job match history",
    description="Retrieve history of all job matches with statistics",
)
async def get_history(
    limit: int = Query(default=50, ge=1, le=100, description="Maximum items to return"),
    service: JobMatchingService = Depends(get_job_service),
) -> JobHistoryResponse:
    """Get job match history"""
    try:
        return service.get_history(limit=limit)
    except Exception as e:
        logger.error(f"History retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/history/{match_id}",
    response_model=dict,
    responses={
        404: {"model": ErrorResponse, "description": "Match not found"},
    },
    summary="Get specific match details",
    description="Retrieve details of a specific job match by ID",
)
async def get_match(
    match_id: str,
    service: JobMatchingService = Depends(get_job_service),
):
    """Get a specific job match by ID"""
    try:
        match = service.get_match_by_id(match_id)
        if match is None:
            raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
        return match
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Match retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/analytics",
    response_model=SkillsAnalytics,
    summary="Get skills analytics",
    description="Analyze your skills across all job matches to identify strengths and areas for improvement",
)
async def get_analytics(
    service: JobMatchingService = Depends(get_job_service),
) -> SkillsAnalytics:
    """Get skills analytics across all job matches"""
    try:
        return service.get_skills_analytics()
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/history",
    summary="Clear job match history",
    description="Delete all job match history",
)
async def clear_history(
    service: JobMatchingService = Depends(get_job_service),
):
    """Clear all job match history"""
    try:
        service._save_history([])
        return {"message": "History cleared successfully"}
    except Exception as e:
        logger.error(f"History clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
