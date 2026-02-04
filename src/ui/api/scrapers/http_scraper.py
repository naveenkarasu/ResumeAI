"""
HTTP-based Job Scrapers

Lightweight scrapers using httpx + BeautifulSoup for sites that
don't require heavy JavaScript rendering. These are faster and
more reliable than browser-based approaches.
"""

import httpx
import re
import gzip
import json
import logging
from typing import List, Optional, AsyncGenerator, Dict, Any
from datetime import datetime, date
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode, quote_plus

from .base_scraper import BaseScraper, ScrapedJob, register_scraper

logger = logging.getLogger(__name__)


class HTTPBasedScraper(BaseScraper):
    """
    Base class for HTTP-based scrapers using httpx + BeautifulSoup.

    Much faster and more reliable than Playwright for sites that
    don't require JavaScript rendering.
    """

    RATE_LIMIT_SECONDS = 2

    def __init__(self):
        super().__init__()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
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

    async def _fetch_html(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse HTML from URL"""
        try:
            await self._rate_limit()
            client = await self._get_client()
            response = await client.get(url)

            if response.status_code == 200:
                return BeautifulSoup(response.text, "html.parser")
            else:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return None

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None


@register_scraper("remoteok")
class RemoteOKScraper(HTTPBasedScraper):
    """
    Scraper for RemoteOK.com - Remote job listings.

    RemoteOK provides a JSON API that's easy to use.
    """

    @property
    def source_name(self) -> str:
        return "remoteok"

    @property
    def base_url(self) -> str:
        return "https://remoteok.com"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client without compression to avoid RemoteOK encoding issues"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                    # No Accept-Encoding to get uncompressed response
                }
            )
        return self._client

    async def search(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> AsyncGenerator[ScrapedJob, None]:
        """Search RemoteOK jobs via their JSON API"""
        # RemoteOK has a JSON API
        api_url = f"{self.base_url}/api"

        try:
            client = await self._get_client()
            response = await client.get(api_url)

            if response.status_code != 200:
                logger.warning(f"RemoteOK API returned {response.status_code}")
                return

            jobs = response.json()
            if jobs and isinstance(jobs[0], dict) and "legal" in jobs[0]:
                jobs = jobs[1:]

            keywords_lower = [k.lower() for k in keywords] if keywords else []

            for job in jobs:
                # Filter by keywords
                if keywords_lower:
                    title = job.get("position", "").lower()
                    company = job.get("company", "").lower()
                    tags = " ".join(job.get("tags", [])).lower()

                    if not any(k in title or k in company or k in tags for k in keywords_lower):
                        continue

                # Parse date
                posted_date = None
                date_str = job.get("date")
                if date_str:
                    try:
                        posted_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
                    except:
                        pass

                # Parse salary
                salary_min = job.get("salary_min")
                salary_max = job.get("salary_max")
                salary_text = None
                if salary_min and salary_max:
                    salary_text = f"${salary_min:,} - ${salary_max:,}"
                elif salary_min:
                    salary_text = f"${salary_min:,}+"

                yield ScrapedJob(
                    url=job.get("url", f"{self.base_url}/remote-jobs/{job.get('slug', '')}"),
                    title=job.get("position", "Unknown"),
                    company_name=job.get("company", "Unknown"),
                    description=job.get("description", ""),
                    source=self.source_name,
                    location="Remote",
                    location_type="remote",
                    salary_text=salary_text,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    posted_date=posted_date,
                    company_logo=job.get("company_logo"),
                    requirements=job.get("tags", []),
                    raw_data=job
                )

        except Exception as e:
            logger.error(f"Error searching RemoteOK: {e}")

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        """Get job details - API already provides full info"""
        return None


@register_scraper("hackernews")
class HackerNewsJobsScraper(HTTPBasedScraper):
    """
    Scraper for Hacker News "Who is Hiring" threads.

    Monthly threads with high-quality tech job postings.
    """

    @property
    def source_name(self) -> str:
        return "hackernews"

    @property
    def base_url(self) -> str:
        return "https://hacker-news.firebaseio.com/v0"

    async def _get_hiring_thread_id(self) -> Optional[int]:
        """Find the latest 'Who is Hiring' thread"""
        # Search for recent "Who is Hiring" posts by whoishiring user
        user_url = f"{self.base_url}/user/whoishiring.json"

        try:
            client = await self._get_client()
            response = await client.get(user_url)
            if response.status_code != 200:
                return None

            user_data = response.json()
            submitted = user_data.get("submitted", [])

            # Check recent submissions for hiring thread
            for item_id in submitted[:10]:
                item_url = f"{self.base_url}/item/{item_id}.json"
                item_response = await client.get(item_url)
                if item_response.status_code == 200:
                    item = item_response.json()
                    title = item.get("title", "")
                    if "Who is hiring" in title:
                        return item_id

            return None

        except Exception as e:
            logger.error(f"Error finding HN hiring thread: {e}")
            return None

    async def search(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> AsyncGenerator[ScrapedJob, None]:
        """Search HN Who is Hiring thread"""
        thread_id = await self._get_hiring_thread_id()
        if not thread_id:
            logger.warning("Could not find HN hiring thread")
            return

        # Get thread with comments
        thread_url = f"{self.base_url}/item/{thread_id}.json"

        try:
            client = await self._get_client()
            response = await client.get(thread_url)
            if response.status_code != 200:
                return

            thread = response.json()
            comment_ids = thread.get("kids", [])[:100]  # Limit to first 100 comments

            keywords_lower = [k.lower() for k in keywords] if keywords else []
            location_lower = location.lower() if location else None

            for comment_id in comment_ids:
                comment_url = f"{self.base_url}/item/{comment_id}.json"
                await self._rate_limit()

                comment_response = await client.get(comment_url)
                if comment_response.status_code != 200:
                    continue

                comment = comment_response.json()
                if comment.get("deleted") or comment.get("dead"):
                    continue

                text = comment.get("text", "")
                if not text:
                    continue

                # Parse job posting from comment
                job = self._parse_hn_comment(comment)
                if not job:
                    continue

                # Filter by keywords
                if keywords_lower:
                    text_lower = text.lower()
                    if not any(k in text_lower for k in keywords_lower):
                        continue

                # Filter by location
                if location_lower:
                    if location_lower == "remote":
                        if job.location_type != "remote":
                            continue
                    elif job.location and location_lower not in job.location.lower():
                        continue

                yield job

        except Exception as e:
            logger.error(f"Error searching HN jobs: {e}")

    def _parse_hn_comment(self, comment: Dict[str, Any]) -> Optional[ScrapedJob]:
        """Parse a HN job posting comment"""
        text = comment.get("text", "")
        if not text:
            return None

        # Clean HTML
        soup = BeautifulSoup(text, "html.parser")
        clean_text = soup.get_text("\n", strip=True)
        lines = clean_text.split("\n")

        if not lines:
            return None

        # First line usually has: Company | Location | Role | etc.
        first_line = lines[0]
        parts = [p.strip() for p in first_line.split("|")]

        company = parts[0] if parts else "Unknown"

        # Try to extract title, location from parts
        title = "Software Engineer"  # Default
        location = None
        location_type = None

        for part in parts[1:]:
            part_lower = part.lower()

            # Check for remote
            if "remote" in part_lower:
                location_type = "remote"
                if not location:
                    location = "Remote"
            elif "hybrid" in part_lower:
                location_type = "hybrid"
            elif "onsite" in part_lower or "on-site" in part_lower:
                location_type = "onsite"

            # Check for common job title keywords
            if any(kw in part_lower for kw in ["engineer", "developer", "manager", "designer", "analyst"]):
                title = part

            # Check for location (city, state pattern)
            if re.match(r"[A-Za-z\s]+,\s*[A-Z]{2}", part) or "USA" in part or "UK" in part:
                location = part

        # Parse date from timestamp
        posted_date = None
        timestamp = comment.get("time")
        if timestamp:
            try:
                posted_date = datetime.fromtimestamp(timestamp).date()
            except:
                pass

        # Look for URLs in the text
        url = f"https://news.ycombinator.com/item?id={comment.get('id')}"

        # Extract any linked URLs
        links = soup.find_all("a")
        for link in links:
            href = link.get("href", "")
            if "jobs" in href or "careers" in href or "greenhouse" in href or "lever" in href:
                url = href
                break

        return ScrapedJob(
            url=url,
            title=title,
            company_name=company,
            description=clean_text,
            source=self.source_name,
            location=location,
            location_type=location_type,
            posted_date=posted_date,
            raw_data=comment
        )

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        """HN comments are self-contained"""
        return None


@register_scraper("weworkremotely")
class WeWorkRemotelyScraper(HTTPBasedScraper):
    """
    Scraper for WeWorkRemotely.com - Remote job board.
    """

    @property
    def source_name(self) -> str:
        return "weworkremotely"

    @property
    def base_url(self) -> str:
        return "https://weworkremotely.com"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client with WeWorkRemotely-specific headers"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Cache-Control": "max-age=0",
                    "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"Windows"',
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1",
                }
            )
        return self._client

    async def search(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> AsyncGenerator[ScrapedJob, None]:
        """Search WeWorkRemotely jobs"""
        # They have category pages we can scrape
        categories = [
            "remote-jobs/programming",
            "remote-jobs/devops-sysadmin",
            "remote-jobs/design",
            "remote-jobs/product",
        ]

        keywords_lower = [k.lower() for k in keywords] if keywords else []

        for category in categories:
            url = f"{self.base_url}/{category}"
            soup = await self._fetch_html(url)

            if not soup:
                continue

            # Find job listings
            job_items = soup.select("li.feature, li.new-feature, ul.jobs li")

            for item in job_items:
                try:
                    link = item.select_one("a[href*='/remote-jobs/']")
                    if not link:
                        continue

                    job_url = urljoin(self.base_url, link.get("href", ""))

                    # Extract info from listing
                    title_el = item.select_one(".title")
                    company_el = item.select_one(".company")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""

                    if not title or not company:
                        continue

                    # Filter by keywords
                    if keywords_lower:
                        text_lower = f"{title} {company}".lower()
                        if not any(k in text_lower for k in keywords_lower):
                            continue

                    # Get logo if available
                    logo_el = item.select_one("div.flag-logo, img.logo")
                    logo = None
                    if logo_el:
                        logo = logo_el.get("style", "")
                        if "url(" in logo:
                            logo = re.search(r"url\(['\"]?([^'\"]+)['\"]?\)", logo)
                            logo = logo.group(1) if logo else None
                        elif logo_el.name == "img":
                            logo = logo_el.get("src")

                    yield ScrapedJob(
                        url=job_url,
                        title=title,
                        company_name=company,
                        description="",  # Would need to fetch detail page
                        source=self.source_name,
                        location="Remote",
                        location_type="remote",
                        company_logo=logo,
                    )

                except Exception as e:
                    logger.debug(f"Error parsing WWR listing: {e}")
                    continue

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        """Get full job details from listing page"""
        soup = await self._fetch_html(url)
        if not soup:
            return None

        try:
            title = soup.select_one("h1.listing-header-container")
            title = title.get_text(strip=True) if title else ""

            company = soup.select_one(".company-card h2, .listing-header-container + p")
            company = company.get_text(strip=True) if company else ""

            description = soup.select_one(".listing-container")
            description = description.get_text("\n", strip=True) if description else ""

            return ScrapedJob(
                url=url,
                title=title,
                company_name=company,
                description=description,
                source=self.source_name,
                location="Remote",
                location_type="remote",
            )

        except Exception as e:
            logger.error(f"Error parsing WWR job details: {e}")
            return None
