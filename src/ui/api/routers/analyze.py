"""Job Analyzer API router"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import logging

from ..dependencies import get_rag
from ..services.analyzer_service import AnalyzerService
from ..models.requests import AnalyzeJobRequest
from ..models.responses import AnalysisResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analyze", tags=["analyze"])

# Service instance
_analyzer_service: Optional[AnalyzerService] = None


def get_analyzer_service() -> AnalyzerService:
    """Get or create analyzer service instance"""
    global _analyzer_service
    if _analyzer_service is None:
        rag = get_rag()
        _analyzer_service = AnalyzerService(rag)
    return _analyzer_service


@router.post(
    "/job",
    response_model=AnalysisResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    summary="Analyze job description",
    description="Analyze a job description against your resume to see match score, gaps, and suggestions",
)
async def analyze_job(
    request: AnalyzeJobRequest,
    service: AnalyzerService = Depends(get_analyzer_service),
) -> AnalysisResponse:
    """Analyze a job description"""
    try:
        result = await service.analyze(
            job_description=request.job_description,
            focus_areas=request.focus_areas,
        )
        return result
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/keywords",
    response_model=list[str],
    summary="Extract keywords from job description",
    description="Extract important keywords from a job description",
)
async def extract_keywords(
    request: AnalyzeJobRequest,
    service: AnalyzerService = Depends(get_analyzer_service),
) -> list[str]:
    """Extract keywords from job description"""
    try:
        parsed = service.parse_job_description(request.job_description)
        return parsed.keywords
    except Exception as e:
        logger.error(f"Keyword extraction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
