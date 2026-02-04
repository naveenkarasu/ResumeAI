"""Y Combinator (Work at a Startup) job scraper"""

from typing import List, Optional, AsyncGenerator, Dict
from datetime import date, datetime
import re
import logging
import json
import asyncio

from .base_scraper import BaseScraper, ScrapedJob, register_scraper

logger = logging.getLogger(__name__)


@register_scraper("ycombinator")
class YCombinatorScraper(BaseScraper):
    """
    Scraper for Y Combinator's Work at a Startup job board.

    This is one of the best sources for startup jobs with high-quality
    YC-backed companies. Has a public API-like interface.

    URL: https://www.workatastartup.com/
    """

    RATE_LIMIT_SECONDS = 3  # YC is relatively friendly
    MAX_PAGES = 10

    @property
    def source_name(self) -> str:
        return "ycombinator"

    @property
    def base_url(self) -> str:
        return "https://www.workatastartup.com"

    def _build_search_url(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        page: int = 1,
        filters: Optional[Dict] = None
    ) -> str:
        """Build Work at a Startup search URL"""
        # The site uses query params for filtering
        url = f"{self.base_url}/jobs"
        params = []

        if keywords:
            query = " ".join(keywords)
            params.append(f"query={query.replace(' ', '+')}")

        if location:
            if location.lower() == "remote":
                params.append("remote=true")
            else:
                params.append(f"location={location.replace(' ', '+')}")

        if filters:
            # Role type filter
            if filters.get("role_type"):
                params.append(f"role={filters['role_type']}")

            # Experience level
            if filters.get("experience_level"):
                exp_map = {
                    "entry": "entry",
                    "mid": "mid",
                    "senior": "senior",
                    "lead": "lead",
                    "executive": "executive"
                }
                if filters["experience_level"] in exp_map:
                    params.append(f"experience={exp_map[filters['experience_level']]}")

            # Company size
            if filters.get("company_size"):
                params.append(f"companySize={filters['company_size']}")

            # Industry/sector
            if filters.get("industry"):
                params.append(f"industry={filters['industry']}")

        if page > 1:
            params.append(f"page={page}")

        if params:
            url += "?" + "&".join(params)

        return url

    async def search(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> AsyncGenerator[ScrapedJob, None]:
        """Search Work at a Startup for jobs"""
        filters = filters or {}
        page = 1

        logger.info(f"Starting YC search: keywords={keywords}, location={location}")

        while page <= self.MAX_PAGES:
            url = self._build_search_url(keywords, location, page, filters)

            logger.debug(f"Scraping YC page {page}: {url}")

            if not await self._navigate(url):
                logger.warning(f"Failed to navigate to YC search page {page}")
                break

            # Wait for job listings to load
            await self._wait_for_selector("[class*='JobListing'], [class*='job-card'], .job-listing", timeout=10000)

            # Scroll to load more content
            for _ in range(5):
                await self._human_scroll()
                await self._random_delay(0.3, 0.6)

            # Try to find job cards - YC uses various class names
            job_cards = await self._query_selector_all(
                "[class*='JobListing'], [class*='job-card'], .job-listing, [data-testid='job-card']"
            )

            # Fallback: try to find job links directly
            if not job_cards:
                job_cards = await self._query_selector_all("a[href*='/jobs/']")

            if not job_cards:
                logger.info(f"No more jobs found on page {page}")
                break

            jobs_found = 0
            seen_urls = set()

            for card in job_cards:
                try:
                    job = await self._parse_job_card(card)
                    if job and job.url not in seen_urls:
                        seen_urls.add(job.url)
                        jobs_found += 1
                        yield job
                except Exception as e:
                    logger.warning(f"Failed to parse YC job card: {e}")
                    continue

            logger.info(f"Found {jobs_found} jobs on YC page {page}")

            if jobs_found == 0:
                break

            page += 1
            await self._random_delay(2, 4)

    async def _parse_job_card(self, card) -> Optional[ScrapedJob]:
        """Parse a job card element into ScrapedJob (async)"""
        try:
            # Get job URL - this might be the card itself or a child link
            job_url = None

            # Check if card is a link
            tag_name = await card.evaluate("el => el.tagName")
            if tag_name.lower() == "a":
                job_url = await card.get_attribute("href")
            else:
                # Find link within card
                link = await card.query_selector("a[href*='/jobs/'], a[href*='/company/']")
                if link:
                    job_url = await link.get_attribute("href")

            if not job_url:
                return None

            if not job_url.startswith("http"):
                job_url = f"{self.base_url}{job_url}"

            # Get title
            title_el = await card.query_selector(
                "h2, h3, [class*='title'], [class*='Title'], .job-title"
            )
            title = (await title_el.inner_text()).strip() if title_el else ""

            if not title:
                # Try getting from link text
                link = await card.query_selector("a")
                if link:
                    title = (await link.inner_text()).strip()

            if not title:
                return None

            # Get company name
            company_el = await card.query_selector(
                "[class*='company'], [class*='Company'], .company-name, [data-testid='company-name']"
            )
            company_name = (await company_el.inner_text()).strip() if company_el else "YC Startup"

            # Get location
            location_el = await card.query_selector(
                "[class*='location'], [class*='Location'], .location"
            )
            location = (await location_el.inner_text()).strip() if location_el else None
            location_type = self._parse_location_type(location) if location else None

            # Remote badge
            remote_badge = await card.query_selector("[class*='remote'], [class*='Remote']")
            if remote_badge and not location_type:
                location_type = "remote"

            # Get salary if shown
            salary_el = await card.query_selector(
                "[class*='salary'], [class*='Salary'], [class*='compensation']"
            )
            salary_text = (await salary_el.inner_text()).strip() if salary_el else None
            salary_min, salary_max, salary_currency = self._parse_salary(salary_text) if salary_text else (None, None, "USD")

            # Company stage/info
            stage_el = await card.query_selector("[class*='stage'], [class*='Stage'], [class*='batch']")
            company_size = None
            if stage_el:
                stage_text = (await stage_el.inner_text()).strip().lower()
                if any(x in stage_text for x in ["seed", "early", "pre-seed"]):
                    company_size = "startup"
                elif any(x in stage_text for x in ["series a", "series b"]):
                    company_size = "small"
                elif any(x in stage_text for x in ["series c", "series d", "growth"]):
                    company_size = "medium"

            # Get company logo
            logo_el = await card.query_selector("img[src*='logo'], img[class*='logo']")
            company_logo = await logo_el.get_attribute("src") if logo_el else None

            # Description snippet
            desc_el = await card.query_selector(
                "[class*='description'], [class*='Description'], p"
            )
            description = (await desc_el.inner_text()).strip() if desc_el else ""

            return ScrapedJob(
                url=job_url,
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
                company_logo=company_logo,
                company_size=company_size,
            )

        except Exception as e:
            logger.error(f"Error parsing YC job card: {e}")
            return None

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        """Get full job details from listing page"""
        logger.debug(f"Fetching YC job details: {url}")

        if not await self._navigate(url):
            return None

        # Wait for content to load
        await self._wait_for_selector("[class*='JobDetail'], [class*='job-detail'], main", timeout=10000)

        try:
            # Title
            title = await self._get_text("h1, [class*='title'], [class*='Title']")

            # Company
            company_name = await self._get_text(
                "[class*='company-name'], [class*='CompanyName'], a[href*='/company/']"
            )

            # Location
            location = await self._get_text("[class*='location'], [class*='Location']")
            location_type = self._parse_location_type(location)

            # Check for remote tag
            remote_el = await self._query_selector("[class*='remote'], [class*='Remote']")
            if remote_el and not location_type:
                location_type = "remote"

            # Salary
            salary_text = await self._get_text("[class*='salary'], [class*='Salary'], [class*='compensation']")
            salary_min, salary_max, salary_currency = self._parse_salary(salary_text)

            # Full description
            description = await self._get_text(
                "[class*='description'], [class*='Description'], [class*='job-content'], article"
            )
            description = self._clean_description(description)

            # Extract requirements
            requirements = self._extract_requirements(description)

            # Company info
            company_logo = await self._get_attribute("img[class*='logo'], img[src*='logo']", "src")

            # YC batch info
            batch_text = await self._get_text("[class*='batch'], [class*='Batch']")

            # Company website
            website_el = await self._query_selector("a[href*='://'][class*='website'], a[href*='://']:not([href*='workatastartup'])")
            company_website = await website_el.get_attribute("href") if website_el else None

            # Industry/sector
            industry = await self._get_text("[class*='industry'], [class*='Industry'], [class*='sector']")

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
                company_logo=company_logo,
                company_website=company_website,
                company_industry=industry,
                company_size="startup",  # YC companies are startups
                raw_data={"yc_batch": batch_text} if batch_text else {},
            )

        except Exception as e:
            logger.error(f"Error getting YC job details: {e}")
            return None
