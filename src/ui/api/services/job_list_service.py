"""Job List Service - Main orchestrator for job search and management"""

import asyncio
import hashlib
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from src.rag import ResumeRAG
from ..database.job_database import JobDatabase, get_job_database
from ..scrapers import (
    get_scraper,
    get_all_scrapers,
    ScrapedJob,
    get_cached_or_search,
    search_jobs as orchestrator_search,
)
from ..models.job_list_models import (
    JobSearchRequest,
    JobSearchResponse,
    JobListing,
    JobListingBrief,
    JobFilters,
    Company,
    Application,
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationListResponse,
    SavedSearch,
    SavedSearchCreate,
    ScrapeStatus,
    MatchQuality,
    LocationType,
    CompanySize,
    ApplicationStatus,
    JobSource,
    QueryParseResult,
    JobRecommendation,
)

logger = logging.getLogger(__name__)


class JobListService:
    """
    Main service for job listing operations.

    Coordinates:
    - Job scraping from multiple sources
    - Database storage and caching
    - Resume matching and scoring
    - Application tracking
    - AI-powered features (query parsing, recommendations)
    """

    def __init__(self, rag: ResumeRAG, db: Optional[JobDatabase] = None):
        self.rag = rag
        self.db = db or get_job_database()
        self._scrape_tasks: Dict[str, asyncio.Task] = {}

    # ============== Search Operations ==============

    async def search_jobs(self, request: JobSearchRequest) -> JobSearchResponse:
        """
        Search for jobs with optional scraping.

        1. Parse NL query if provided
        2. Check cache for recent results
        3. Search database
        4. Optionally trigger background scraping
        5. Calculate match scores
        6. Return paginated results
        """
        # Parse natural language query
        filters = request.filters or JobFilters()

        if request.query:
            parsed = await self._parse_query(request.query)
            filters = self._merge_filters(filters, parsed.filters)

        # Generate cache key
        cache_key = self._generate_cache_key(filters)

        # Check cache first
        cached = self.db.get_cached_search(cache_key)
        if cached:
            logger.info(f"Cache hit for search: {cache_key[:16]}")
            job_ids = cached["result_job_ids"]
            # Fetch jobs from DB
            jobs, total = self._get_jobs_by_ids(
                job_ids,
                limit=request.limit,
                offset=(request.page - 1) * request.limit
            )
        else:
            # Search database
            jobs, total = self.db.search_jobs(
                keywords=filters.keywords,
                location_type=[lt.value for lt in filters.location_type] if filters.location_type else None,
                salary_min=filters.salary_min,
                salary_max=filters.salary_max,
                sources=[s.value for s in filters.sources] if filters.sources else None,
                posted_within_days=filters.posted_within_days,
                limit=request.limit,
                offset=(request.page - 1) * request.limit,
                sort_by=request.sort_by if request.sort_by != "match_score" else "posted_date",
                sort_order=request.sort_order,
            )

            # Trigger background scraping if few results
            if total < 20:
                asyncio.create_task(self._background_scrape(filters))

        # Calculate match scores if requested
        if request.include_match_scores and jobs:
            jobs = await self._add_match_scores(jobs)

            # Sort by match score if requested
            if request.sort_by == "match_score":
                jobs = sorted(
                    jobs,
                    key=lambda j: j.get("match_score", 0) or 0,
                    reverse=(request.sort_order == "desc")
                )

        # Convert to response models
        job_briefs = [self._to_job_brief(job) for job in jobs]

        # Calculate pagination
        pages = (total + request.limit - 1) // request.limit if total > 0 else 1

        return JobSearchResponse(
            jobs=job_briefs,
            total=total,
            page=request.page,
            pages=pages,
            limit=request.limit,
            search_id=cache_key[:16],
            cached=cached is not None,
            scrape_status=ScrapeStatus.COMPLETED,
            filters_applied=filters,
        )

    async def get_job_details(self, job_id: str) -> Optional[JobListing]:
        """Get full job details with match analysis"""
        job = self.db.get_job(job_id)
        if not job:
            return None

        # Get match score
        job_with_score = await self._add_match_scores([job])
        job = job_with_score[0] if job_with_score else job

        # Get application status if exists
        apps, _ = self.db.get_applications()
        app_status = None
        for app in apps:
            if app.get("job_id") == job_id:
                app_status = app.get("status")
                break

        return self._to_job_listing(job, app_status)

    def _get_jobs_by_ids(self, job_ids: List[str], limit: int, offset: int) -> Tuple[List[Dict], int]:
        """Fetch jobs by IDs with pagination"""
        # This would be more efficient with a proper IN query
        jobs = []
        for jid in job_ids[offset:offset + limit]:
            job = self.db.get_job(jid)
            if job:
                jobs.append(job)
        return jobs, len(job_ids)

    # ============== Query Parsing ==============

    async def _parse_query(self, query: str) -> QueryParseResult:
        """Parse natural language query into structured filters using LLM"""
        prompt = f"""Parse this job search query into structured filters.

Query: "{query}"

Extract JSON with these fields (use null for fields not mentioned):
- keywords: list of job-related terms
- location: location string or "remote"
- location_type: "remote", "hybrid", or "onsite"
- salary_min: minimum salary as integer
- salary_max: maximum salary as integer
- company_size: "startup", "small", "medium", "large", or "enterprise"
- experience_level: "entry", "mid", "senior", or "lead"
- industry: industry if mentioned

Return ONLY valid JSON."""

        try:
            response = await self.rag.chat(prompt, task_type="default")

            # Parse response as JSON
            import json
            # Extract JSON from response
            json_match = response
            if "```" in response:
                json_match = response.split("```")[1]
                if json_match.startswith("json"):
                    json_match = json_match[4:]

            parsed = json.loads(json_match.strip())

            # Convert to JobFilters
            filters = JobFilters(
                keywords=parsed.get("keywords", []),
                location=parsed.get("location"),
                location_type=[LocationType(parsed["location_type"])] if parsed.get("location_type") else [],
                salary_min=parsed.get("salary_min"),
                salary_max=parsed.get("salary_max"),
                company_size=[CompanySize(parsed["company_size"])] if parsed.get("company_size") else [],
                experience_level=parsed.get("experience_level"),
                industry=parsed.get("industry"),
            )

            # Generate interpretation
            interpretation = self._generate_interpretation(filters)

            return QueryParseResult(
                original_query=query,
                filters=filters,
                confidence=0.8,
                interpretation=interpretation,
            )

        except Exception as e:
            logger.warning(f"Failed to parse query with LLM: {e}")
            # Fallback: simple keyword extraction
            keywords = [w for w in query.split() if len(w) > 2]
            return QueryParseResult(
                original_query=query,
                filters=JobFilters(keywords=keywords),
                confidence=0.3,
                interpretation=f"Searching for: {', '.join(keywords)}",
            )

    def _generate_interpretation(self, filters: JobFilters) -> str:
        """Generate human-readable interpretation of filters"""
        parts = []

        if filters.keywords:
            parts.append(f"jobs matching '{' '.join(filters.keywords)}'")

        if filters.location_type:
            types = [lt.value for lt in filters.location_type]
            parts.append(f"{'/'.join(types)} positions")

        if filters.salary_min:
            parts.append(f"paying ${filters.salary_min:,}+")

        if filters.company_size:
            sizes = [cs.value for cs in filters.company_size]
            parts.append(f"at {'/'.join(sizes)} companies")

        return "Searching for " + ", ".join(parts) if parts else "Searching all jobs"

    def _merge_filters(self, base: JobFilters, parsed: JobFilters) -> JobFilters:
        """Merge parsed filters with base filters (parsed takes precedence)"""
        return JobFilters(
            keywords=parsed.keywords or base.keywords,
            location=parsed.location or base.location,
            location_type=parsed.location_type or base.location_type,
            salary_min=parsed.salary_min or base.salary_min,
            salary_max=parsed.salary_max or base.salary_max,
            company_size=parsed.company_size or base.company_size,
            sources=base.sources,  # Keep user's source preference
            posted_within_days=base.posted_within_days,
            experience_level=parsed.experience_level or base.experience_level,
            industry=parsed.industry or base.industry,
            # Preserve dork parameters from base (user-selected)
            dork_id=base.dork_id,
            dork_category=base.dork_category,
        )

    def _generate_cache_key(self, filters: JobFilters) -> str:
        """Generate cache key from filters"""
        key_data = f"{filters.keywords}|{filters.location_type}|{filters.salary_min}|{filters.sources}"
        return hashlib.md5(key_data.encode()).hexdigest()

    # ============== Match Scoring ==============

    async def _add_match_scores(self, jobs: List[Dict]) -> List[Dict]:
        """Add match scores to jobs based on resume"""
        # Get resume context
        resume_context = self.rag.get_relevant_context("skills experience education")
        resume_hash = hashlib.md5(resume_context.encode()).hexdigest()[:16]

        for job in jobs:
            # Check cache first
            cached_score = self.db.get_match_score(job["id"], resume_hash)

            if cached_score:
                job["match_score"] = cached_score["overall_score"]
                job["matched_skills"] = cached_score["matched_skills"]
                job["missing_skills"] = cached_score["missing_skills"]
            else:
                # Calculate match score
                score_data = await self._calculate_match_score(job, resume_context)
                job.update(score_data)

                # Cache the score
                self.db.save_match_score(job["id"], resume_hash, score_data)

            # Set match quality
            job["match_quality"] = self._determine_quality(job.get("match_score", 0))

        return jobs

    async def _calculate_match_score(self, job: Dict, resume_context: str) -> Dict:
        """Calculate match score between job and resume"""
        description = job.get("description", "")
        requirements = job.get("requirements", [])

        if isinstance(requirements, str):
            import json
            requirements = json.loads(requirements) if requirements else []

        # Simple keyword matching for now
        # In production, use embeddings similarity
        resume_lower = resume_context.lower()
        desc_lower = description.lower()

        # Extract skills from requirements
        matched = []
        missing = []

        common_skills = [
            "python", "javascript", "typescript", "java", "go", "rust", "c++",
            "react", "vue", "angular", "node", "django", "fastapi", "flask",
            "aws", "gcp", "azure", "docker", "kubernetes", "terraform",
            "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
            "machine learning", "deep learning", "nlp", "computer vision",
            "git", "ci/cd", "agile", "scrum"
        ]

        for skill in common_skills:
            in_job = skill in desc_lower or any(skill in r.lower() for r in requirements)
            in_resume = skill in resume_lower

            if in_job:
                if in_resume:
                    matched.append(skill.title())
                else:
                    missing.append(skill.title())

        # Calculate score
        total_required = len(matched) + len(missing)
        if total_required > 0:
            skills_score = (len(matched) / total_required) * 100
        else:
            skills_score = 50  # Neutral if no skills to compare

        # Weight other factors (simplified)
        overall_score = skills_score  # Could add experience, education, etc.

        return {
            "overall_score": round(overall_score, 1),
            "skills_score": round(skills_score, 1),
            "matched_skills": matched[:10],
            "missing_skills": missing[:10],
        }

    def _determine_quality(self, score: float) -> str:
        """Determine match quality from score"""
        if score >= 85:
            return MatchQuality.EXCELLENT.value
        elif score >= 70:
            return MatchQuality.GOOD.value
        elif score >= 50:
            return MatchQuality.FAIR.value
        else:
            return MatchQuality.POOR.value

    # ============== Scraping ==============

    async def _background_scrape(self, filters: JobFilters, force_refresh: bool = False):
        """
        Trigger background scraping using the new orchestrator.

        Uses the orchestrator for parallel execution with:
        - Automatic retry with backoff
        - Fallback sources on failure
        - Result caching (6-hour TTL)
        - Proxy rotation
        """
        try:
            keywords = filters.keywords or ["software engineer"]
            location = filters.location or "remote"
            sources = [s.value for s in filters.sources] if filters.sources else None

            # Build filters dict including dork parameters
            scraper_filters = {
                "location_type": [lt.value for lt in filters.location_type] if filters.location_type else None
            }

            # Add dork parameters if specified
            if filters.dork_id:
                scraper_filters["dork_id"] = filters.dork_id
            if filters.dork_category:
                scraper_filters["dork_category"] = filters.dork_category

            # Use the new cached orchestrator
            result = await get_cached_or_search(
                keywords=keywords,
                location=location,
                filters=scraper_filters,
                sources=sources,
                force_refresh=force_refresh,
            )

            # Save results to database
            job_count = 0
            for job in result.jobs:
                await self._save_scraped_job(job)
                job_count += 1

            logger.info(
                f"Scrape completed: {job_count} jobs from {len(result.sources_succeeded)} sources "
                f"({', '.join(result.sources_succeeded)}). "
                f"Failed: {result.sources_failed}. Cached: {result.cached}"
            )

        except Exception as e:
            logger.error(f"Background scrape failed: {e}")

    async def _save_scraped_job(self, scraped: ScrapedJob):
        """Save scraped job to database"""
        # Get or create company
        company_id = self.db.get_or_create_company(
            scraped.company_name,
            logo_url=scraped.company_logo,
            website=scraped.company_website,
            industry=scraped.company_industry,
            size=scraped.company_size,
        )

        # Insert job
        job_data = scraped.to_dict()
        job_data["company_id"] = company_id
        self.db.insert_job(job_data)

    async def trigger_scrape(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        sources: Optional[List[str]] = None,
        force_refresh: bool = False,
    ) -> str:
        """
        Manually trigger a scrape operation, returns task ID.

        Args:
            keywords: Search keywords
            location: Location filter (or "remote")
            sources: Specific sources to use (None = all available)
            force_refresh: If True, bypass cache and fetch fresh results

        Returns:
            Task ID for status tracking
        """
        task_id = f"scrape_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        filters = JobFilters(
            keywords=keywords,
            location=location,
            sources=[JobSource(s) for s in sources] if sources else [],
        )

        task = asyncio.create_task(self._background_scrape(filters, force_refresh=force_refresh))
        self._scrape_tasks[task_id] = task

        return task_id

    def get_scrape_status(self, task_id: str) -> ScrapeStatus:
        """Get status of a scrape task"""
        task = self._scrape_tasks.get(task_id)
        if not task:
            return ScrapeStatus.COMPLETED

        if task.done():
            return ScrapeStatus.COMPLETED
        else:
            return ScrapeStatus.IN_PROGRESS

    # ============== Application Tracking ==============

    def create_application(self, data: ApplicationCreate) -> Application:
        """Create or update application for a job"""
        app_id = self.db.create_application(
            job_id=data.job_id,
            status=data.status.value,
            notes=data.notes,
            resume_version=data.resume_version,
            reminder_date=data.reminder_date.isoformat() if data.reminder_date else None,
        )

        return self.get_application(app_id)

    def update_application(self, app_id: str, data: ApplicationUpdate) -> Optional[Application]:
        """Update an existing application"""
        # Get current application
        app = self.db.get_application(app_id)
        if not app:
            return None

        # Update with new data
        update_kwargs = {}
        if data.status:
            update_kwargs["status"] = data.status.value
        if data.notes is not None:
            update_kwargs["notes"] = data.notes
        if data.cover_letter is not None:
            update_kwargs["cover_letter"] = data.cover_letter
        if data.reminder_date is not None:
            update_kwargs["reminder_date"] = data.reminder_date.isoformat()

        if update_kwargs:
            self.db.create_application(
                job_id=app["job_id"],
                **update_kwargs
            )

        return self.get_application(app_id)

    def get_application(self, app_id: str) -> Optional[Application]:
        """Get application details"""
        app = self.db.get_application(app_id)
        if not app:
            return None

        return self._to_application(app)

    def get_applications(
        self,
        status: Optional[ApplicationStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> ApplicationListResponse:
        """Get all applications"""
        apps, total = self.db.get_applications(
            status=status.value if status else None,
            limit=limit,
            offset=offset,
        )

        # Get status counts
        stats = self.db.get_application_stats()

        return ApplicationListResponse(
            applications=[self._to_application(app) for app in apps],
            total=total,
            by_status=stats.get("by_status", {}),
        )

    def delete_application(self, app_id: str) -> bool:
        """Delete an application"""
        return self.db.delete_application(app_id)

    def get_due_reminders(self) -> List[Application]:
        """Get applications with due reminders"""
        apps = self.db.get_applications_due_reminder()
        return [self._to_application(app) for app in apps]

    # ============== Saved Searches ==============

    def save_search(self, data: SavedSearchCreate) -> SavedSearch:
        """Save a search preset"""
        filters_dict = data.filters.model_dump() if data.filters else {}

        search_id = self.db.save_search(
            name=data.name,
            query=data.query,
            filters=filters_dict,
            notification_enabled=data.notification_enabled,
        )

        searches = self.db.get_saved_searches()
        for s in searches:
            if s["id"] == search_id:
                return self._to_saved_search(s)

        raise ValueError("Failed to save search")

    def get_saved_searches(self) -> List[SavedSearch]:
        """Get all saved searches"""
        searches = self.db.get_saved_searches()
        return [self._to_saved_search(s) for s in searches]

    def delete_saved_search(self, search_id: str) -> bool:
        """Delete a saved search"""
        return self.db.delete_saved_search(search_id)

    # ============== AI Features ==============

    async def get_recommendations(self, limit: int = 10) -> List[JobRecommendation]:
        """Get AI-recommended jobs based on resume"""
        # Get recent jobs
        jobs, _ = self.db.search_jobs(
            posted_within_days=14,
            limit=100,
        )

        if not jobs:
            return []

        # Add match scores
        jobs = await self._add_match_scores(jobs)

        # Sort by match score and take top N
        jobs = sorted(jobs, key=lambda j: j.get("match_score", 0) or 0, reverse=True)
        top_jobs = jobs[:limit]

        # Generate recommendations with reasons
        recommendations = []
        for job in top_jobs:
            matched = job.get("matched_skills", [])
            reason = f"Matches your skills in {', '.join(matched[:3])}" if matched else "Good fit based on your experience"

            recommendations.append(JobRecommendation(
                job=self._to_job_brief(job),
                recommendation_reason=reason,
                relevance_score=job.get("match_score", 0) or 0,
            ))

        return recommendations

    async def generate_cover_letter(self, job_id: str, custom_prompt: Optional[str] = None) -> str:
        """Generate a cover letter for a job"""
        job = self.db.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        # Get resume context
        resume_context = self.rag.get_relevant_context("experience skills achievements education")

        # Get match data
        job_with_match = await self._add_match_scores([job])
        job = job_with_match[0]

        matched_skills = job.get("matched_skills", [])
        missing_skills = job.get("missing_skills", [])

        prompt = f"""Write a compelling cover letter for this job application.

JOB DETAILS:
Title: {job['title']}
Company: {job.get('company_name', 'the company')}
Description: {job['description'][:1000]}

CANDIDATE RESUME:
{resume_context}

MATCHED SKILLS: {', '.join(matched_skills)}
SKILLS TO ADDRESS: {', '.join(missing_skills[:3])}

{f'ADDITIONAL INSTRUCTIONS: {custom_prompt}' if custom_prompt else ''}

Guidelines:
- Keep it under 300 words
- Lead with strongest matching qualifications
- Address 1-2 missing skills with transferable experience
- Show genuine interest in the company
- End with clear call to action
- Be professional but personable

Write the cover letter now:"""

        response = await self.rag.chat(prompt, task_type="email_draft")
        return response

    # ============== Stats ==============

    def get_job_stats(self) -> Dict:
        """Get job statistics"""
        return self.db.get_job_stats()

    def get_application_stats(self) -> Dict:
        """Get application statistics"""
        return self.db.get_application_stats()

    # ============== Conversion Helpers ==============

    def _safe_job_source(self, source: str) -> JobSource:
        """Safely convert source string to JobSource enum"""
        try:
            return JobSource(source)
        except ValueError:
            # Fallback for unknown sources - try to map common prefixes
            source_lower = source.lower()
            for js in JobSource:
                if source_lower.startswith(js.value):
                    return js
            # Default fallback
            return JobSource.INDEED

    def _to_job_brief(self, job: Dict) -> JobListingBrief:
        """Convert database job to JobListingBrief"""
        return JobListingBrief(
            id=job["id"],
            title=job["title"],
            company_name=job.get("company_name", "Unknown"),
            company_logo=job.get("company_logo"),
            location=job.get("location"),
            location_type=LocationType(job["location_type"]) if job.get("location_type") else None,
            salary_text=job.get("salary_text") or self._format_salary(job.get("salary_min"), job.get("salary_max")),
            posted_date=date.fromisoformat(job["posted_date"]) if job.get("posted_date") else None,
            source=self._safe_job_source(job["source"]),
            match_score=job.get("match_score"),
            match_quality=MatchQuality(job["match_quality"]) if job.get("match_quality") else None,
            application_status=ApplicationStatus(job["application_status"]) if job.get("application_status") else None,
        )

    def _to_job_listing(self, job: Dict, app_status: Optional[str] = None) -> JobListing:
        """Convert database job to full JobListing"""
        company = Company(
            id=job.get("company_id", "unknown"),
            name=job.get("company_name", "Unknown"),
            logo_url=job.get("company_logo"),
            industry=job.get("company_industry"),
            size=CompanySize(job["company_size"]) if job.get("company_size") else None,
            rating=job.get("company_rating"),
        )

        requirements = job.get("requirements", [])
        if isinstance(requirements, str):
            import json
            requirements = json.loads(requirements) if requirements else []

        return JobListing(
            id=job["id"],
            url=job["url"],
            title=job["title"],
            company=company,
            location=job.get("location"),
            location_type=LocationType(job["location_type"]) if job.get("location_type") else None,
            salary_min=job.get("salary_min"),
            salary_max=job.get("salary_max"),
            salary_currency=job.get("salary_currency", "USD"),
            salary_text=job.get("salary_text"),
            description=job["description"],
            requirements=requirements,
            posted_date=date.fromisoformat(job["posted_date"]) if job.get("posted_date") else None,
            scraped_at=datetime.fromisoformat(job["scraped_at"]) if job.get("scraped_at") else datetime.now(),
            source=self._safe_job_source(job["source"]),
            is_active=job.get("is_active", True),
            match_score=job.get("match_score"),
            match_quality=MatchQuality(job["match_quality"]) if job.get("match_quality") else None,
            matched_skills=job.get("matched_skills", []),
            missing_skills=job.get("missing_skills", []),
            application_status=ApplicationStatus(app_status) if app_status else None,
        )

    def _to_application(self, app: Dict) -> Application:
        """Convert database application to Application model"""
        job_brief = JobListingBrief(
            id=app.get("job_id", ""),
            title=app.get("job_title", "Unknown"),
            company_name=app.get("company_name", "Unknown"),
            company_logo=app.get("company_logo"),
            location=app.get("job_location"),
            location_type=LocationType(app["job_location_type"]) if app.get("job_location_type") else None,
            source=JobSource(app["job_source"]) if app.get("job_source") else JobSource.INDEED,
        )

        from ..models.job_list_models import ApplicationTimelineEntry

        timeline = [
            ApplicationTimelineEntry(
                old_status=ApplicationStatus(t["old_status"]) if t.get("old_status") else None,
                new_status=ApplicationStatus(t["new_status"]),
                changed_at=datetime.fromisoformat(t["changed_at"]) if t.get("changed_at") else datetime.now(),
                notes=t.get("notes"),
            )
            for t in app.get("timeline", [])
        ]

        return Application(
            id=app["id"],
            job=job_brief,
            status=ApplicationStatus(app["status"]),
            applied_date=date.fromisoformat(app["applied_date"]) if app.get("applied_date") else None,
            notes=app.get("notes"),
            resume_version=app.get("resume_version"),
            cover_letter=app.get("cover_letter"),
            reminder_date=date.fromisoformat(app["reminder_date"]) if app.get("reminder_date") else None,
            last_updated=datetime.fromisoformat(app["last_updated"]) if app.get("last_updated") else datetime.now(),
            timeline=timeline,
        )

    def _to_saved_search(self, search: Dict) -> SavedSearch:
        """Convert database saved search to SavedSearch model"""
        filters_dict = search.get("filters", {})
        filters = JobFilters(**filters_dict) if filters_dict else JobFilters()

        return SavedSearch(
            id=search["id"],
            name=search["name"],
            query=search.get("query"),
            filters=filters,
            created_at=datetime.fromisoformat(search["created_at"]) if search.get("created_at") else datetime.now(),
            last_run_at=datetime.fromisoformat(search["last_run_at"]) if search.get("last_run_at") else None,
            notification_enabled=search.get("notification_enabled", False),
        )

    def _format_salary(self, min_sal: Optional[int], max_sal: Optional[int]) -> Optional[str]:
        """Format salary range as string"""
        if min_sal and max_sal:
            return f"${min_sal:,} - ${max_sal:,}"
        elif min_sal:
            return f"${min_sal:,}+"
        elif max_sal:
            return f"Up to ${max_sal:,}"
        return None


# Singleton instance
_service_instance: Optional[JobListService] = None


def get_job_list_service(rag: ResumeRAG) -> JobListService:
    """Get or create JobListService instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = JobListService(rag)
    return _service_instance
