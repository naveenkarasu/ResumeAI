"""Indeed job scraper"""

from typing import List, Optional, AsyncGenerator, Dict
from datetime import date
import re
import logging
import asyncio

from .base_scraper import BaseScraper, ScrapedJob, register_scraper

logger = logging.getLogger(__name__)


@register_scraper("indeed")
class IndeedScraper(BaseScraper):
    """
    Scraper for Indeed.com job listings.

    Indeed is one of the largest job aggregators with good coverage
    across industries and locations.
    """

    RATE_LIMIT_SECONDS = 5  # Conservative to avoid blocks
    MAX_PAGES = 5

    @property
    def source_name(self) -> str:
        return "indeed"

    @property
    def base_url(self) -> str:
        return "https://www.indeed.com"

    def _build_search_url(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        start: int = 0,
        filters: Optional[Dict] = None
    ) -> str:
        """Build Indeed search URL"""
        query = "+".join(keywords)
        url = f"{self.base_url}/jobs?q={query}"

        if location:
            url += f"&l={location.replace(' ', '+')}"

        if start > 0:
            url += f"&start={start}"

        # Add filters
        if filters:
            if filters.get("remote"):
                url += "&sc=0kf%3Aattr%28DSQF7%29%3B"  # Remote filter

            if filters.get("salary_min"):
                # Indeed uses specific salary format
                salary = filters["salary_min"]
                url += f"&salary={salary}"

            if filters.get("posted_within_days"):
                days = filters["posted_within_days"]
                if days <= 1:
                    url += "&fromage=1"
                elif days <= 3:
                    url += "&fromage=3"
                elif days <= 7:
                    url += "&fromage=7"
                elif days <= 14:
                    url += "&fromage=14"

            if filters.get("job_type"):
                job_type = filters["job_type"]
                type_map = {
                    "full-time": "fulltime",
                    "part-time": "parttime",
                    "contract": "contract",
                    "internship": "internship"
                }
                if job_type in type_map:
                    url += f"&jt={type_map[job_type]}"

        return url

    async def search(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> AsyncGenerator[ScrapedJob, None]:
        """Search Indeed for jobs"""
        filters = filters or {}
        page = 0
        jobs_per_page = 15

        logger.info(f"Starting Indeed search: keywords={keywords}, location={location}")

        while page < self.MAX_PAGES:
            start = page * jobs_per_page
            url = self._build_search_url(keywords, location, start, filters)

            logger.debug(f"Scraping Indeed page {page + 1}: {url}")

            if not await self._navigate(url):
                logger.warning(f"Failed to navigate to Indeed search page {page + 1}")
                break

            # Wait for job cards to load
            await self._wait_for_selector(".job_seen_beacon, .jobsearch-ResultsList", timeout=10000)

            # Scroll to load lazy content
            for _ in range(3):
                await self._human_scroll()

            # Extract job cards using async methods
            job_cards = await self._query_selector_all(".job_seen_beacon, .resultContent")

            if not job_cards:
                logger.info(f"No more jobs found on page {page + 1}")
                break

            jobs_found = 0
            for card in job_cards:
                try:
                    job = await self._parse_job_card(card)
                    if job:
                        jobs_found += 1
                        yield job
                except Exception as e:
                    logger.warning(f"Failed to parse Indeed job card: {e}")
                    continue

            logger.info(f"Found {jobs_found} jobs on Indeed page {page + 1}")

            if jobs_found < jobs_per_page // 2:
                # Fewer jobs than expected, probably last page
                break

            page += 1
            await self._random_delay(2, 4)

    async def _parse_job_card(self, card) -> Optional[ScrapedJob]:
        """Parse a job card element into ScrapedJob (async)"""
        try:
            # Get job title and URL
            title_el = await card.query_selector("h2.jobTitle a, a.jcs-JobTitle")
            if not title_el:
                return None

            title = (await title_el.inner_text()).strip()
            job_url = await title_el.get_attribute("href")

            if job_url and not job_url.startswith("http"):
                job_url = f"{self.base_url}{job_url}"

            # Get company name
            company_el = await card.query_selector("[data-testid='company-name'], .companyName")
            company_name = (await company_el.inner_text()).strip() if company_el else "Unknown"

            # Get location
            location_el = await card.query_selector("[data-testid='text-location'], .companyLocation")
            location = (await location_el.inner_text()).strip() if location_el else None

            # Parse location type
            location_type = self._parse_location_type(location) if location else None

            # Get salary if available
            salary_el = await card.query_selector(".salary-snippet-container, .estimated-salary, [data-testid='attribute_snippet_testid']")
            salary_text = None
            salary_min = None
            salary_max = None
            salary_currency = "USD"

            if salary_el:
                salary_text = (await salary_el.inner_text()).strip()
                salary_min, salary_max, salary_currency = self._parse_salary(salary_text)

            # Get posted date
            date_el = await card.query_selector(".date, [data-testid='myJobsStateDate']")
            posted_text = (await date_el.inner_text()).strip() if date_el else None
            posted_date = self._parse_posted_date(posted_text) if posted_text else None

            # Get job snippet/description preview
            snippet_el = await card.query_selector(".job-snippet, [data-testid='job-snippet']")
            snippet = (await snippet_el.inner_text()).strip() if snippet_el else ""

            return ScrapedJob(
                url=job_url,
                title=title,
                company_name=company_name,
                description=snippet,  # Will be expanded in get_job_details
                source=self.source_name,
                location=location,
                location_type=location_type,
                salary_text=salary_text,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=salary_currency,
                posted_date=posted_date,
                posted_text=posted_text,
            )

        except Exception as e:
            logger.error(f"Error parsing Indeed job card: {e}")
            return None

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        """Get full job details from listing page"""
        logger.debug(f"Fetching Indeed job details: {url}")

        if not await self._navigate(url):
            return None

        # Wait for job description
        await self._wait_for_selector("#jobDescriptionText, .jobsearch-JobComponent-description", timeout=10000)

        try:
            # Title
            title = await self._get_text("h1.jobsearch-JobInfoHeader-title, [data-testid='job-title']")

            # Company
            company_name = await self._get_text("[data-testid='inlineHeader-companyName'], .jobsearch-InlineCompanyRating a")

            # Location
            location = await self._get_text("[data-testid='job-location'], .jobsearch-JobInfoHeader-subtitle > div:nth-child(2)")
            location_type = self._parse_location_type(location)

            # Salary
            salary_text = await self._get_text("#salaryInfoAndJobType, [data-testid='attribute_snippet_testid']")
            salary_min, salary_max, salary_currency = self._parse_salary(salary_text)

            # Full description
            description = await self._get_text("#jobDescriptionText, .jobsearch-JobComponent-description")
            description = self._clean_description(description)

            # Extract requirements from description
            requirements = self._extract_requirements(description)

            return ScrapedJob(
                url=url,
                title=title,
                company_name=company_name,
                description=description,
                source=self.source_name,
                location=location,
                location_type=location_type,
                salary_text=salary_text,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=salary_currency,
                requirements=requirements,
            )

        except Exception as e:
            logger.error(f"Error getting Indeed job details: {e}")
            return None
