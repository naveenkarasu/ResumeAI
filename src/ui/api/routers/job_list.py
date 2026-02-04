"""Job List API Router"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Optional, List
import logging

from ..dependencies import get_rag
from ..services.job_list_service import JobListService, get_job_list_service
from ..models.job_list_models import (
    JobSearchRequest,
    JobSearchResponse,
    JobListing,
    JobListingBrief,
    Application,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationListResponse,
    SavedSearch,
    SavedSearchCreate,
    JobRecommendation,
    CoverLetterRequest,
    CoverLetterResponse,
    JobSearchStats,
    ApplicationStats,
    ApplicationStatus,
    ScrapeStatus,
)
from ..models.responses import ErrorResponse
from ..scrapers.google_dorking_scraper import get_dork_strategies, get_dork_categories

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/job-list", tags=["job-list"])

# Service dependency
_service: Optional[JobListService] = None


def get_service() -> JobListService:
    """Get or create JobListService instance"""
    global _service
    if _service is None:
        rag = get_rag()
        _service = get_job_list_service(rag)
    return _service


# ============== Search Endpoints ==============

@router.post(
    "/search",
    response_model=JobSearchResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Search for jobs",
    description="Search for jobs using natural language query and/or structured filters",
)
async def search_jobs(
    request: JobSearchRequest,
    service: JobListService = Depends(get_service),
) -> JobSearchResponse:
    """
    Search for jobs with natural language and filters.

    Supports:
    - Natural language queries: "remote ML engineer jobs $150k+ at startups"
    - Structured filters: location, salary, company size, sources
    - Resume matching: returns match scores against your resume
    - Pagination and sorting
    """
    try:
        if not request.query and not request.filters:
            raise HTTPException(
                status_code=400,
                detail="Either query or filters must be provided"
            )
        return await service.search_jobs(request)
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/jobs",
    response_model=JobSearchResponse,
    summary="Get cached jobs",
    description="Get paginated list of cached jobs with optional filters",
)
async def get_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("posted_date", pattern="^(match_score|posted_date|salary)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    location_type: Optional[str] = Query(None, description="Filter by remote/hybrid/onsite"),
    source: Optional[str] = Query(None, description="Filter by source"),
    service: JobListService = Depends(get_service),
) -> JobSearchResponse:
    """Get paginated jobs from cache"""
    from ..models.job_list_models import JobFilters, LocationType, JobSource

    filters = JobFilters()
    if location_type:
        filters.location_type = [LocationType(location_type)]
    if source:
        filters.sources = [JobSource(source)]

    request = JobSearchRequest(
        filters=filters,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        include_match_scores=True,
    )

    return await service.search_jobs(request)


@router.get(
    "/jobs/{job_id}",
    response_model=JobListing,
    responses={404: {"model": ErrorResponse}},
    summary="Get job details",
    description="Get full job details with match analysis",
)
async def get_job_details(
    job_id: str,
    service: JobListService = Depends(get_service),
) -> JobListing:
    """Get detailed job information with match scores"""
    job = await service.get_job_details(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ============== Recommendations ==============

@router.get(
    "/recommendations",
    response_model=List[JobRecommendation],
    summary="Get AI job recommendations",
    description="Get personalized job recommendations based on your resume",
)
async def get_recommendations(
    limit: int = Query(10, ge=1, le=50),
    service: JobListService = Depends(get_service),
) -> List[JobRecommendation]:
    """Get AI-powered job recommendations"""
    return await service.get_recommendations(limit)


# ============== Application Tracking ==============

@router.get(
    "/applications",
    response_model=ApplicationListResponse,
    summary="Get tracked applications",
    description="Get all tracked job applications with status",
)
async def get_applications(
    status: Optional[ApplicationStatus] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: JobListService = Depends(get_service),
) -> ApplicationListResponse:
    """Get tracked applications"""
    return service.get_applications(status=status, limit=limit, offset=offset)


@router.post(
    "/applications",
    response_model=Application,
    responses={400: {"model": ErrorResponse}},
    summary="Track a job application",
    description="Start tracking a job application",
)
async def create_application(
    data: ApplicationCreate,
    service: JobListService = Depends(get_service),
) -> Application:
    """Create or update application tracking"""
    try:
        return service.create_application(data)
    except Exception as e:
        logger.error(f"Create application error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/applications/{app_id}",
    response_model=Application,
    responses={404: {"model": ErrorResponse}},
    summary="Get application details",
)
async def get_application(
    app_id: str,
    service: JobListService = Depends(get_service),
) -> Application:
    """Get application details with timeline"""
    app = service.get_application(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.put(
    "/applications/{app_id}",
    response_model=Application,
    responses={404: {"model": ErrorResponse}},
    summary="Update application status",
)
async def update_application(
    app_id: str,
    data: ApplicationUpdate,
    service: JobListService = Depends(get_service),
) -> Application:
    """Update application status or details"""
    app = service.update_application(app_id, data)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.delete(
    "/applications/{app_id}",
    summary="Delete application tracking",
)
async def delete_application(
    app_id: str,
    service: JobListService = Depends(get_service),
) -> dict:
    """Stop tracking an application"""
    success = service.delete_application(app_id)
    if not success:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"success": True, "message": "Application deleted"}


@router.get(
    "/applications/reminders/due",
    response_model=List[Application],
    summary="Get due reminders",
)
async def get_due_reminders(
    service: JobListService = Depends(get_service),
) -> List[Application]:
    """Get applications with reminders due today or overdue"""
    return service.get_due_reminders()


# ============== Cover Letter Generation ==============

@router.post(
    "/jobs/{job_id}/cover-letter",
    response_model=CoverLetterResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Generate cover letter",
    description="Generate a tailored cover letter for a job",
)
async def generate_cover_letter(
    job_id: str,
    request: Optional[CoverLetterRequest] = None,
    service: JobListService = Depends(get_service),
) -> CoverLetterResponse:
    """Generate AI cover letter for a job"""
    try:
        custom_prompt = request.custom_prompt if request else None
        cover_letter = await service.generate_cover_letter(job_id, custom_prompt)

        # Get job for response
        job = await service.get_job_details(job_id)

        return CoverLetterResponse(
            job_id=job_id,
            cover_letter=cover_letter,
            word_count=len(cover_letter.split()),
            highlights_used=job.matched_skills if job else [],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Cover letter generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Saved Searches ==============

@router.get(
    "/saved-searches",
    response_model=List[SavedSearch],
    summary="Get saved searches",
)
async def get_saved_searches(
    service: JobListService = Depends(get_service),
) -> List[SavedSearch]:
    """Get all saved search presets"""
    return service.get_saved_searches()


@router.post(
    "/saved-searches",
    response_model=SavedSearch,
    summary="Save a search",
)
async def save_search(
    data: SavedSearchCreate,
    service: JobListService = Depends(get_service),
) -> SavedSearch:
    """Save a search preset for quick access"""
    return service.save_search(data)


@router.delete(
    "/saved-searches/{search_id}",
    summary="Delete saved search",
)
async def delete_saved_search(
    search_id: str,
    service: JobListService = Depends(get_service),
) -> dict:
    """Delete a saved search"""
    success = service.delete_saved_search(search_id)
    if not success:
        raise HTTPException(status_code=404, detail="Search not found")
    return {"success": True, "message": "Search deleted"}


# ============== Scraping Control ==============

@router.post(
    "/scrape",
    summary="Trigger job scraping",
    description="Manually trigger scraping from job sites",
)
async def trigger_scrape(
    keywords: List[str] = Query(..., min_length=1),
    location: Optional[str] = None,
    sources: Optional[List[str]] = None,
    background_tasks: BackgroundTasks = None,
    service: JobListService = Depends(get_service),
) -> dict:
    """Trigger background scraping"""
    task_id = await service.trigger_scrape(keywords, location, sources)
    return {
        "task_id": task_id,
        "status": "started",
        "message": f"Scraping started for keywords: {keywords}"
    }


@router.get(
    "/scrape/status/{task_id}",
    summary="Get scrape status",
)
async def get_scrape_status(
    task_id: str,
    service: JobListService = Depends(get_service),
) -> dict:
    """Get status of a scraping task"""
    status = service.get_scrape_status(task_id)
    return {"task_id": task_id, "status": status.value}


# ============== Google Dorking ==============

@router.get(
    "/dork-strategies",
    summary="Get available dork strategies",
    description="Get all available Google dorking strategies organized by category",
)
async def get_dork_strategies_endpoint() -> dict:
    """Get all dork strategies for the UI selector"""
    return get_dork_strategies()


@router.get(
    "/dork-categories",
    summary="Get dork categories",
    description="Get list of dork categories for dropdown",
)
async def get_dork_categories_endpoint() -> list:
    """Get dork categories for dropdown"""
    return get_dork_categories()


# ============== Statistics ==============

@router.get(
    "/stats/jobs",
    response_model=JobSearchStats,
    summary="Get job statistics",
)
async def get_job_stats(
    service: JobListService = Depends(get_service),
) -> JobSearchStats:
    """Get job database statistics"""
    stats = service.get_job_stats()
    return JobSearchStats(
        total_jobs_indexed=stats.get("total_jobs", 0),
        jobs_by_source=stats.get("by_source", {}),
        jobs_by_location_type=stats.get("by_location_type", {}),
        average_salary=stats.get("average_salary"),
        last_scrape_at=stats.get("last_scrape"),
    )


@router.get(
    "/stats/applications",
    response_model=ApplicationStats,
    summary="Get application statistics",
)
async def get_application_stats(
    service: JobListService = Depends(get_service),
) -> ApplicationStats:
    """Get application tracking statistics"""
    stats = service.get_application_stats()
    return ApplicationStats(
        total_applications=stats.get("total", 0),
        by_status=stats.get("by_status", {}),
        response_rate=stats.get("response_rate"),
    )
