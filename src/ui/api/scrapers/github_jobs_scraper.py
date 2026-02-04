"""
GitHub Jobs Scraper

Fetches job listings from curated GitHub repositories that maintain
job listings in JSON format. These are community-maintained and updated
regularly via GitHub Actions.

Sources:
- SimplifyJobs/New-Grad-Positions
- SimplifyJobs/Summer2026-Internships
- jobright-ai repos
"""

import httpx
import json
import logging
from typing import List, Optional, AsyncGenerator, Dict, Any
from datetime import datetime, date
from dataclasses import dataclass

from .base_scraper import BaseScraper, ScrapedJob, register_scraper

logger = logging.getLogger(__name__)


@dataclass
class GitHubJobSource:
    """Configuration for a GitHub job source"""
    name: str
    owner: str
    repo: str
    json_path: str
    job_type: str  # "new_grad", "internship", etc.
    branch: str = "dev"  # Default branch is dev for most job repos


# GitHub repositories that maintain job listings
GITHUB_JOB_SOURCES = [
    GitHubJobSource(
        name="SimplifyJobs New Grad",
        owner="SimplifyJobs",
        repo="New-Grad-Positions",
        json_path=".github/scripts/listings.json",
        job_type="new_grad",
        branch="dev"
    ),
    GitHubJobSource(
        name="SimplifyJobs Internships 2026",
        owner="SimplifyJobs",
        repo="Summer2026-Internships",
        json_path=".github/scripts/listings.json",
        job_type="internship",
        branch="dev"
    ),
]


@register_scraper("github")
class GitHubJobsScraper(BaseScraper):
    """
    Scraper for GitHub-hosted job listings.

    These repositories are community-maintained and regularly updated
    via GitHub Actions. They provide structured JSON data that's easy
    to parse and doesn't require browser automation.
    """

    RATE_LIMIT_SECONDS = 1  # GitHub API is fast

    @property
    def source_name(self) -> str:
        return "github"

    @property
    def base_url(self) -> str:
        return "https://raw.githubusercontent.com"

    def __init__(self, sources: Optional[List[GitHubJobSource]] = None):
        super().__init__()
        self.sources = sources or GITHUB_JOB_SOURCES
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                }
            )
        return self._client

    async def _close_client(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_client()

    async def _fetch_json(self, source: GitHubJobSource) -> List[Dict[str, Any]]:
        """Fetch job listings JSON from GitHub"""
        url = f"{self.base_url}/{source.owner}/{source.repo}/{source.branch}/{source.json_path}"

        try:
            client = await self._get_client()
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Fetched {len(data)} jobs from {source.name}")
                return data
            else:
                logger.warning(f"Failed to fetch {source.name}: HTTP {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching {source.name}: {e}")
            return []

    def _parse_listing(self, item: Dict[str, Any], source: GitHubJobSource) -> Optional[ScrapedJob]:
        """Parse a single listing from JSON"""
        try:
            # Skip inactive listings
            if not item.get("active", True):
                return None
            if not item.get("is_visible", True):
                return None

            # Extract basic info
            title = item.get("title", "")
            company = item.get("company_name", "")
            url = item.get("url", "")

            if not title or not company or not url:
                return None

            # Parse locations
            locations = item.get("locations", [])
            location = ", ".join(locations) if locations else None

            # Determine location type
            location_type = None
            if locations:
                loc_text = " ".join(locations).lower()
                if "remote" in loc_text:
                    location_type = "remote"
                elif "hybrid" in loc_text:
                    location_type = "hybrid"
                else:
                    location_type = "onsite"

            # Parse date
            posted_date = None
            date_posted = item.get("date_posted")
            if date_posted:
                try:
                    # Unix timestamp
                    posted_date = datetime.fromtimestamp(date_posted).date()
                except (ValueError, TypeError):
                    pass

            return ScrapedJob(
                url=url,
                title=title,
                company_name=company,
                description=f"{source.job_type.replace('_', ' ').title()} position at {company}",
                source=self.source_name,  # Use scraper's source_name (github, simplify, or jobright)
                location=location,
                location_type=location_type,
                posted_date=posted_date,
                job_type=source.job_type,
                raw_data=item
            )

        except Exception as e:
            logger.debug(f"Error parsing listing: {e}")
            return None

    async def search(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> AsyncGenerator[ScrapedJob, None]:
        """
        Search GitHub job repositories.

        Args:
            keywords: Keywords to match in title/company
            location: Location filter (supports "remote")
            filters: Additional filters (job_type: "new_grad" or "internship")
        """
        filters = filters or {}
        job_type_filter = filters.get("job_type")
        keywords_lower = [k.lower() for k in keywords] if keywords else []
        location_lower = location.lower() if location else None

        for source in self.sources:
            # Filter by job type if specified
            if job_type_filter and source.job_type != job_type_filter:
                continue

            logger.info(f"Fetching from {source.name}")
            listings = await self._fetch_json(source)

            for item in listings:
                job = self._parse_listing(item, source)
                if not job:
                    continue

                # Apply keyword filter - search in title, company, tags, roles, and locations
                if keywords_lower:
                    # Build searchable text from multiple fields
                    searchable_parts = [
                        job.title.lower(),
                        job.company_name.lower(),
                        job.description.lower() if job.description else "",
                        job.location.lower() if job.location else "",
                    ]
                    # Add raw data fields that might contain relevant info
                    raw = job.raw_data or {}
                    if raw.get("terms"):
                        searchable_parts.extend([t.lower() for t in raw.get("terms", [])])
                    if raw.get("categories"):
                        searchable_parts.extend([c.lower() for c in raw.get("categories", [])])
                    if raw.get("role"):
                        searchable_parts.append(raw.get("role", "").lower())
                    if raw.get("season"):
                        searchable_parts.append(raw.get("season", "").lower())

                    searchable_text = " ".join(searchable_parts)
                    if not any(k in searchable_text for k in keywords_lower):
                        continue

                # Apply location filter
                if location_lower:
                    if location_lower == "remote":
                        if job.location_type != "remote":
                            continue
                    elif job.location:
                        if location_lower not in job.location.lower():
                            continue
                    else:
                        continue

                yield job

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        """
        GitHub repos only have basic info, so we return what we have.
        For full details, you'd need to scrape the actual job posting URL.
        """
        # Could implement actual URL scraping here if needed
        return None


@register_scraper("simplify")
class SimplifyJobsScraper(GitHubJobsScraper):
    """Scraper specifically for SimplifyJobs repositories"""

    @property
    def source_name(self) -> str:
        return "simplify"

    def __init__(self):
        # Only use SimplifyJobs sources
        simplify_sources = [s for s in GITHUB_JOB_SOURCES if s.owner == "SimplifyJobs"]
        super().__init__(sources=simplify_sources if simplify_sources else GITHUB_JOB_SOURCES)


@register_scraper("jobright")
class JobrightScraper(GitHubJobsScraper):
    """Scraper specifically for Jobright-ai repositories (shares SimplifyJobs data)"""

    @property
    def source_name(self) -> str:
        return "jobright"

    def __init__(self):
        # Jobright doesn't have a public JSON anymore, use SimplifyJobs
        super().__init__(sources=GITHUB_JOB_SOURCES)
