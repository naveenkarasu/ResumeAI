"""
Scraper Orchestrator

Coordinates multiple scrapers with parallel execution, retry logic,
fallback sources, and partial result aggregation.
"""

import asyncio
import logging
import hashlib
from typing import List, Optional, Dict, Any, AsyncGenerator, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .base_scraper import ScrapedJob, get_all_scrapers, BaseScraper
from .proxy_pool import get_proxy_pool

logger = logging.getLogger(__name__)


class ScraperStatus(Enum):
    """Status of a scraper execution"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ScraperResult:
    """Result from a single scraper"""
    source: str
    status: ScraperStatus
    jobs: List[ScrapedJob] = field(default_factory=list)
    error: Optional[str] = None
    duration_ms: int = 0
    retry_count: int = 0


@dataclass
class OrchestratorResult:
    """Combined result from all scrapers"""
    jobs: List[ScrapedJob]
    total_found: int
    sources_succeeded: List[str]
    sources_failed: List[str]
    sources_partial: List[str]
    duration_ms: int
    cached: bool = False
    cache_key: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "jobs": [j.to_dict() for j in self.jobs],
            "total_found": self.total_found,
            "sources_succeeded": self.sources_succeeded,
            "sources_failed": self.sources_failed,
            "sources_partial": self.sources_partial,
            "duration_ms": self.duration_ms,
            "cached": self.cached,
        }


class ScraperOrchestrator:
    """
    Orchestrates multiple job scrapers with resilience features.

    Features:
    - Parallel execution across all sources
    - Retry with exponential backoff
    - Fallback to alternative sources
    - Partial result aggregation
    - Deduplication by content hash
    - Configurable timeouts
    """

    def __init__(
        self,
        max_retries: int = 3,
        timeout_per_source: int = 60,
        max_parallel: int = 5,
        use_proxies: bool = False,  # Disabled by default for faster HTTP scrapers
    ):
        self.max_retries = max_retries
        self.timeout_per_source = timeout_per_source
        self.max_parallel = max_parallel
        self.use_proxies = use_proxies

        # Source priority (higher = tried first, used for fallback)
        self.source_priority = {
            # Tier 1: Fast and reliable (API/JSON based)
            "github": 100,
            "simplify": 95,
            "jobright": 90,
            "remoteok": 85,
            "hackernews": 80,
            "weworkremotely": 75,
            "google_dork": 70,  # Web search dorking
            # Tier 2: Moderate (HTTP scraping)
            "builtin": 60,
            "ycombinator": 55,
            # Tier 3: Slow/flaky (Browser required)
            "indeed": 40,
            "dice": 35,
            "wellfound": 30,
            "linkedin": 20,
            "glassdoor": 10,
        }

    def _get_cache_key(
        self,
        keywords: List[str],
        location: Optional[str],
        filters: Optional[Dict],
    ) -> str:
        """Generate cache key for search parameters"""
        key_parts = [
            ":".join(sorted(keywords)) if keywords else "",
            location or "",
            hashlib.md5(str(sorted(filters.items()) if filters else "").encode()).hexdigest()[:8],
        ]
        return f"search:{':'.join(key_parts)}"

    async def _run_scraper_with_retry(
        self,
        scraper: BaseScraper,
        keywords: List[str],
        location: Optional[str],
        filters: Optional[Dict],
        proxy: Optional[str] = None,
    ) -> ScraperResult:
        """Run a single scraper with retry logic"""
        source = scraper.source_name
        result = ScraperResult(source=source, status=ScraperStatus.PENDING)
        start_time = datetime.now()

        for attempt in range(self.max_retries):
            try:
                result.retry_count = attempt
                result.status = ScraperStatus.RUNNING

                jobs = []
                async with scraper:
                    async for job in scraper.search(keywords, location, filters):
                        jobs.append(job)

                        # Yield partial results early
                        if len(jobs) >= 50:
                            break

                result.jobs = jobs
                result.status = ScraperStatus.SUCCESS if jobs else ScraperStatus.PARTIAL
                result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

                logger.info(f"[{source}] Found {len(jobs)} jobs in {result.duration_ms}ms")
                return result

            except asyncio.TimeoutError:
                result.status = ScraperStatus.TIMEOUT
                result.error = f"Timeout after {self.timeout_per_source}s"
                logger.warning(f"[{source}] Timeout on attempt {attempt + 1}")

            except RuntimeError as e:
                # Browser scrapers may fail on Windows/uvicorn - don't retry
                if "Browser scrapers not available" in str(e):
                    result.status = ScraperStatus.FAILED
                    result.error = str(e)
                    logger.warning(f"[{source}] Browser scraper unavailable on this platform")
                    result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                    return result
                else:
                    result.error = str(e)
                    logger.warning(f"[{source}] Error on attempt {attempt + 1}: {e}")

            except Exception as e:
                result.error = str(e)
                logger.warning(f"[{source}] Error on attempt {attempt + 1}: {e}")

                # Exponential backoff
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) + (asyncio.get_event_loop().time() % 1)
                    await asyncio.sleep(wait_time)

        result.status = ScraperStatus.FAILED
        result.duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        return result

    async def search(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        filters: Optional[Dict] = None,
        sources: Optional[List[str]] = None,
        min_results: int = 10,
    ) -> OrchestratorResult:
        """
        Search across multiple job sources.

        Args:
            keywords: Search keywords
            location: Location filter (or "remote")
            filters: Additional filters
            sources: Specific sources to use (None = all)
            min_results: Minimum results before stopping early

        Returns:
            OrchestratorResult with aggregated jobs
        """
        start_time = datetime.now()
        cache_key = self._get_cache_key(keywords, location, filters)

        # Get available scrapers
        all_scrapers = get_all_scrapers()

        if sources:
            scrapers_to_use = {k: v for k, v in all_scrapers.items() if k in sources}
        else:
            scrapers_to_use = all_scrapers

        # Sort by priority
        sorted_sources = sorted(
            scrapers_to_use.keys(),
            key=lambda x: self.source_priority.get(x, 0),
            reverse=True
        )

        logger.info(f"Starting search with {len(sorted_sources)} sources: {sorted_sources}")

        # Get proxies if enabled
        proxies = []
        if self.use_proxies:
            try:
                pool = await get_proxy_pool()
                proxies = await pool.get_proxies(len(sorted_sources))
            except Exception as e:
                logger.warning(f"Could not get proxies: {e}")

        # Create scraper instances
        scraper_instances = []
        for source in sorted_sources:
            scraper_class = scrapers_to_use[source]
            try:
                scraper = scraper_class()
                scraper_instances.append(scraper)
            except Exception as e:
                logger.warning(f"Could not instantiate {source}: {e}")

        # Run scrapers in parallel with semaphore
        semaphore = asyncio.Semaphore(self.max_parallel)
        results: List[ScraperResult] = []
        all_jobs: List[ScrapedJob] = []
        seen_hashes: Set[str] = set()

        async def run_with_limit(scraper: BaseScraper, proxy: Optional[str]):
            async with semaphore:
                try:
                    return await asyncio.wait_for(
                        self._run_scraper_with_retry(scraper, keywords, location, filters, proxy),
                        timeout=self.timeout_per_source
                    )
                except asyncio.TimeoutError:
                    return ScraperResult(
                        source=scraper.source_name,
                        status=ScraperStatus.TIMEOUT,
                        error=f"Timeout after {self.timeout_per_source}s"
                    )

        # Assign proxies to scrapers (round-robin if fewer proxies than scrapers)
        tasks = []
        for i, scraper in enumerate(scraper_instances):
            proxy = proxies[i % len(proxies)] if proxies else None
            tasks.append(run_with_limit(scraper, proxy))

        # Gather results
        scraper_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        sources_succeeded = []
        sources_failed = []
        sources_partial = []

        for result in scraper_results:
            if isinstance(result, Exception):
                logger.error(f"Scraper exception: {result}")
                continue

            if not isinstance(result, ScraperResult):
                continue

            results.append(result)

            if result.status == ScraperStatus.SUCCESS:
                sources_succeeded.append(result.source)
            elif result.status == ScraperStatus.PARTIAL:
                sources_partial.append(result.source)
            else:
                sources_failed.append(result.source)

            # Deduplicate jobs by content hash
            for job in result.jobs:
                if job.content_hash not in seen_hashes:
                    seen_hashes.add(job.content_hash)
                    all_jobs.append(job)

        # Sort jobs by posted date (newest first)
        all_jobs.sort(
            key=lambda j: j.posted_date or datetime.min.date(),
            reverse=True
        )

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        logger.info(
            f"Search completed: {len(all_jobs)} jobs from "
            f"{len(sources_succeeded)} sources in {duration_ms}ms"
        )

        return OrchestratorResult(
            jobs=all_jobs,
            total_found=len(all_jobs),
            sources_succeeded=sources_succeeded,
            sources_failed=sources_failed,
            sources_partial=sources_partial,
            duration_ms=duration_ms,
            cached=False,
            cache_key=cache_key,
        )

    async def search_streaming(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        filters: Optional[Dict] = None,
        sources: Optional[List[str]] = None,
    ) -> AsyncGenerator[ScrapedJob, None]:
        """
        Stream search results as they arrive from different sources.

        Yields jobs as soon as they're found, useful for real-time UI updates.
        """
        all_scrapers = get_all_scrapers()

        if sources:
            scrapers_to_use = {k: v for k, v in all_scrapers.items() if k in sources}
        else:
            scrapers_to_use = all_scrapers

        seen_hashes: Set[str] = set()
        queue: asyncio.Queue[Optional[ScrapedJob]] = asyncio.Queue()

        async def run_scraper(source: str, scraper_class):
            try:
                scraper = scraper_class()
                async with scraper:
                    async for job in scraper.search(keywords, location, filters):
                        if job.content_hash not in seen_hashes:
                            seen_hashes.add(job.content_hash)
                            await queue.put(job)
            except Exception as e:
                logger.warning(f"[{source}] Error: {e}")
            finally:
                await queue.put(None)  # Signal completion

        # Start all scrapers
        tasks = [
            asyncio.create_task(run_scraper(source, cls))
            for source, cls in scrapers_to_use.items()
        ]

        completed = 0
        total = len(tasks)

        # Yield jobs as they arrive
        while completed < total:
            job = await queue.get()
            if job is None:
                completed += 1
            else:
                yield job

        # Ensure all tasks complete
        await asyncio.gather(*tasks, return_exceptions=True)


# Convenience function
async def search_jobs(
    keywords: List[str],
    location: Optional[str] = None,
    filters: Optional[Dict] = None,
    sources: Optional[List[str]] = None,
) -> OrchestratorResult:
    """
    Search for jobs across multiple sources.

    This is the main entry point for job searching.
    """
    orchestrator = ScraperOrchestrator()
    return await orchestrator.search(keywords, location, filters, sources)
