"""Wellfound (formerly AngelList Talent) job scraper"""

from typing import List, Optional, AsyncGenerator, Dict
from datetime import date
import re
import logging
import asyncio

from .base_scraper import BaseScraper, ScrapedJob, register_scraper

logger = logging.getLogger(__name__)


@register_scraper("wellfound")
class WellfoundScraper(BaseScraper):
    """
    Scraper for Wellfound (formerly AngelList Talent) job listings.

    Wellfound focuses on startup jobs and is popular among tech startups
    looking for talent. Great for finding early-stage company opportunities.

    URL: https://wellfound.com/jobs
    """

    RATE_LIMIT_SECONDS = 4
    MAX_PAGES = 8

    @property
    def source_name(self) -> str:
        return "wellfound"

    @property
    def base_url(self) -> str:
        return "https://wellfound.com"

    def _build_search_url(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        page: int = 1,
        filters: Optional[Dict] = None
    ) -> str:
        """Build Wellfound search URL"""
        # Wellfound uses role-based URLs
        url = f"{self.base_url}/jobs"

        params = []

        if keywords:
            # Join keywords for search
            query = " ".join(keywords)
            params.append(f"query={query.replace(' ', '%20')}")

        if location:
            if location.lower() == "remote":
                params.append("remote=true")
            else:
                params.append(f"locations[]={location.replace(' ', '%20')}")

        if filters:
            # Remote filter
            if filters.get("remote"):
                params.append("remote=true")

            # Role/job type
            if filters.get("role"):
                params.append(f"role={filters['role']}")

            # Company size
            if filters.get("company_size"):
                size_map = {
                    "startup": "1-10",
                    "small": "11-50",
                    "medium": "51-200",
                    "large": "201-500",
                    "enterprise": "501+"
                }
                if filters["company_size"] in size_map:
                    params.append(f"company_size={size_map[filters['company_size']]}")

            # Salary range
            if filters.get("salary_min"):
                params.append(f"salary_min={filters['salary_min']}")

            # Job type
            if filters.get("job_type"):
                type_map = {
                    "full-time": "full-time",
                    "part-time": "part-time",
                    "contract": "contract",
                    "internship": "internship"
                }
                if filters["job_type"] in type_map:
                    params.append(f"job_type={type_map[filters['job_type']]}")

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
        """Search Wellfound for jobs"""
        filters = filters or {}
        page = 1

        logger.info(f"Starting Wellfound search: keywords={keywords}, location={location}")

        while page <= self.MAX_PAGES:
            url = self._build_search_url(keywords, location, page, filters)

            logger.debug(f"Scraping Wellfound page {page}: {url}")

            if not await self._navigate(url):
                logger.warning(f"Failed to navigate to Wellfound search page {page}")
                break

            # Wait for job cards to load
            await self._wait_for_selector(
                "[class*='styles_jobCard'], [class*='JobCard'], [data-test='startup-jobs-list'] > div",
                timeout=15000
            )

            # Scroll to load lazy content (Wellfound uses infinite scroll)
            for _ in range(5):
                await self._human_scroll()
                await self._random_delay(0.5, 1.0)

            # Extract job cards
            job_cards = await self._query_selector_all(
                "[class*='styles_jobCard'], [class*='JobCard'], [class*='StartupJob'], [data-test='job-listing']"
            )

            # Fallback selector
            if not job_cards:
                job_cards = await self._query_selector_all(
                    "[class*='styles_job'], a[href*='/jobs/']"
                )

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
                    logger.warning(f"Failed to parse Wellfound job card: {e}")
                    continue

            logger.info(f"Found {jobs_found} jobs on Wellfound page {page}")

            if jobs_found < 5:  # Probably last page
                break

            page += 1
            await self._random_delay(2, 4)

    async def _parse_job_card(self, card) -> Optional[ScrapedJob]:
        """Parse a job card element into ScrapedJob (async)"""
        try:
            # Get job URL - try multiple selectors
            job_url = None
            title = None

            # Check if card is a link
            tag_name = await card.evaluate("el => el.tagName")
            if tag_name.lower() == "a":
                job_url = await card.get_attribute("href")
                title_el = await card.query_selector("h2, h3, [class*='title']")
                title = (await title_el.inner_text()).strip() if title_el else (await card.inner_text()).strip()
            else:
                # Find link within card
                title_link = await card.query_selector(
                    "a[href*='/jobs/'], a[class*='title'], h2 a, h3 a"
                )
                if title_link:
                    job_url = await title_link.get_attribute("href")
                    title = (await title_link.inner_text()).strip()

            if not job_url or not title:
                return None

            if not job_url.startswith("http"):
                job_url = f"{self.base_url}{job_url}"

            # Get company name
            company_el = await card.query_selector(
                "[class*='company'], [class*='Company'], a[href*='/company/'], [class*='startup']"
            )
            company_name = (await company_el.inner_text()).strip() if company_el else "Startup"

            # Get location
            location_el = await card.query_selector(
                "[class*='location'], [class*='Location']"
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

            # Company stage/info (Wellfound shows funding stage)
            stage_el = await card.query_selector(
                "[class*='stage'], [class*='Stage'], [class*='funding']"
            )
            company_size = None
            if stage_el:
                stage_text = (await stage_el.inner_text()).strip().lower()
                if any(x in stage_text for x in ["seed", "pre-seed", "angel"]):
                    company_size = "startup"
                elif any(x in stage_text for x in ["series a", "series b"]):
                    company_size = "small"
                elif any(x in stage_text for x in ["series c", "series d", "late"]):
                    company_size = "medium"

            # Company logo
            logo_el = await card.query_selector(
                "img[class*='logo'], img[src*='logo'], img[alt*='logo']"
            )
            company_logo = await logo_el.get_attribute("src") if logo_el else None

            # Description snippet
            desc_el = await card.query_selector(
                "[class*='description'], [class*='Description'], p"
            )
            description = (await desc_el.inner_text()).strip() if desc_el else ""

            # Team size
            team_el = await card.query_selector(
                "[class*='team'], [class*='employee'], [class*='size']"
            )
            if team_el and not company_size:
                team_text = (await team_el.inner_text()).strip().lower()
                if any(x in team_text for x in ["1-10", "< 10"]):
                    company_size = "startup"
                elif any(x in team_text for x in ["11-50", "10-50"]):
                    company_size = "small"
                elif any(x in team_text for x in ["51-200", "50-200"]):
                    company_size = "medium"

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
            logger.error(f"Error parsing Wellfound job card: {e}")
            return None

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        """Get full job details from listing page"""
        logger.debug(f"Fetching Wellfound job details: {url}")

        if not await self._navigate(url):
            return None

        # Wait for job content to load
        await self._wait_for_selector(
            "[class*='JobDetail'], [class*='job-detail'], main, [class*='description']",
            timeout=15000
        )

        try:
            # Title
            title = await self._get_text(
                "h1, [class*='JobTitle'], [class*='job-title']"
            )

            # Company
            company_name = await self._get_text(
                "[class*='company-name'], [class*='CompanyName'], a[href*='/company/']"
            )

            # Location
            location = await self._get_text(
                "[class*='location'], [class*='Location']"
            )
            location_type = self._parse_location_type(location)

            # Remote check
            remote_el = await self._query_selector("[class*='remote'], [class*='Remote']")
            if remote_el and not location_type:
                location_type = "remote"

            # Salary
            salary_text = await self._get_text(
                "[class*='salary'], [class*='Salary'], [class*='compensation']"
            )
            salary_min, salary_max, salary_currency = self._parse_salary(salary_text)

            # Full description
            description = await self._get_text(
                "[class*='description'], [class*='Description'], [class*='job-content'], article"
            )
            description = self._clean_description(description)

            # Extract requirements
            requirements = self._extract_requirements(description)

            # Company info
            company_logo = await self._get_attribute(
                "img[class*='logo'], img[src*='logo']", "src"
            )

            # Company website
            website_el = await self._query_selector(
                "a[href*='://'][class*='website'], a[class*='company-link']"
            )
            company_website = await website_el.get_attribute("href") if website_el else None

            # Industry
            industry = await self._get_text(
                "[class*='industry'], [class*='Industry'], [class*='market']"
            )

            # Funding stage
            stage_text = await self._get_text(
                "[class*='stage'], [class*='funding']"
            )
            company_size = "startup"  # Default for Wellfound
            if stage_text:
                stage_lower = stage_text.lower()
                if any(x in stage_lower for x in ["series c", "series d", "late", "growth"]):
                    company_size = "medium"
                elif any(x in stage_lower for x in ["series a", "series b"]):
                    company_size = "small"

            # Team size
            team_text = await self._get_text(
                "[class*='team-size'], [class*='employees']"
            )

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
                company_size=company_size,
                raw_data={"funding_stage": stage_text, "team_size": team_text} if stage_text or team_text else {},
            )

        except Exception as e:
            logger.error(f"Error getting Wellfound job details: {e}")
            return None
