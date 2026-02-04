"""Dice job scraper"""

from typing import List, Optional, AsyncGenerator, Dict
from datetime import date
import re
import logging
import asyncio

from .base_scraper import BaseScraper, ScrapedJob, register_scraper

logger = logging.getLogger(__name__)


@register_scraper("dice")
class DiceScraper(BaseScraper):
    """
    Scraper for Dice.com job listings.

    Dice is one of the leading tech job boards, specializing in
    technology and engineering positions.

    URL: https://www.dice.com/jobs
    """

    RATE_LIMIT_SECONDS = 4
    MAX_PAGES = 8

    @property
    def source_name(self) -> str:
        return "dice"

    @property
    def base_url(self) -> str:
        return "https://www.dice.com"

    def _build_search_url(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        page: int = 1,
        filters: Optional[Dict] = None
    ) -> str:
        """Build Dice search URL"""
        query = " ".join(keywords)
        url = f"{self.base_url}/jobs?q={query.replace(' ', '%20')}"

        if location:
            if location.lower() == "remote":
                url += "&filters.isRemote=true"
            else:
                url += f"&location={location.replace(' ', '%20')}"

        if page > 1:
            url += f"&page={page}"

        if filters:
            # Remote filter
            if filters.get("remote"):
                url += "&filters.isRemote=true"

            # Employment type
            if filters.get("job_type"):
                type_map = {
                    "full-time": "FULLTIME",
                    "part-time": "PARTTIME",
                    "contract": "CONTRACTS",
                    "third-party": "THIRD_PARTY"
                }
                if filters["job_type"] in type_map:
                    url += f"&filters.employmentType={type_map[filters['job_type']]}"

            # Posted date
            if filters.get("posted_within_days"):
                days = filters["posted_within_days"]
                if days <= 1:
                    url += "&filters.postedDate=ONE"
                elif days <= 3:
                    url += "&filters.postedDate=THREE"
                elif days <= 7:
                    url += "&filters.postedDate=SEVEN"
                elif days <= 30:
                    url += "&filters.postedDate=THIRTY"

            # Easy apply filter
            if filters.get("easy_apply"):
                url += "&filters.easyApply=true"

        return url

    async def search(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> AsyncGenerator[ScrapedJob, None]:
        """Search Dice for jobs"""
        filters = filters or {}
        page = 1

        logger.info(f"Starting Dice search: keywords={keywords}, location={location}")

        while page <= self.MAX_PAGES:
            url = self._build_search_url(keywords, location, page, filters)

            logger.debug(f"Scraping Dice page {page}: {url}")

            if not await self._navigate(url):
                logger.warning(f"Failed to navigate to Dice search page {page}")
                break

            # Wait for job cards to load
            await self._wait_for_selector("[data-cy='search-card'], .card-title-link, [class*='JobCard']", timeout=15000)

            # Scroll to load lazy content
            for _ in range(3):
                await self._human_scroll()
                await self._random_delay(0.5, 1.0)

            # Extract job cards
            job_cards = await self._query_selector_all(
                "[data-cy='search-card'], .search-card, [class*='JobCard']"
            )

            if not job_cards:
                logger.info(f"No more jobs found on page {page}")
                break

            jobs_found = 0
            for card in job_cards:
                try:
                    job = await self._parse_job_card(card)
                    if job:
                        jobs_found += 1
                        yield job
                except Exception as e:
                    logger.warning(f"Failed to parse Dice job card: {e}")
                    continue

            logger.info(f"Found {jobs_found} jobs on Dice page {page}")

            if jobs_found < 10:  # Probably last page
                break

            page += 1
            await self._random_delay(2, 4)

    async def _parse_job_card(self, card) -> Optional[ScrapedJob]:
        """Parse a job card element into ScrapedJob (async)"""
        try:
            # Get job title and URL
            title_el = await card.query_selector(
                "[data-cy='card-title-link'], .card-title-link, a[class*='title']"
            )
            if not title_el:
                return None

            title = (await title_el.inner_text()).strip()
            job_url = await title_el.get_attribute("href")

            if not job_url:
                return None

            if not job_url.startswith("http"):
                job_url = f"{self.base_url}{job_url}"

            # Get company name
            company_el = await card.query_selector(
                "[data-cy='search-result-company-name'], .card-company a, [class*='company']"
            )
            company_name = (await company_el.inner_text()).strip() if company_el else "Unknown"

            # Get location
            location_el = await card.query_selector(
                "[data-cy='search-result-location'], .card-location, [class*='location']"
            )
            location = (await location_el.inner_text()).strip() if location_el else None
            location_type = self._parse_location_type(location) if location else None

            # Remote badge
            remote_badge = await card.query_selector("[class*='remote'], [data-cy*='remote']")
            if remote_badge and not location_type:
                location_type = "remote"

            # Get salary if available
            salary_el = await card.query_selector(
                "[data-cy='compensation'], .card-salary, [class*='salary']"
            )
            salary_text = (await salary_el.inner_text()).strip() if salary_el else None
            salary_min, salary_max, salary_currency = self._parse_salary(salary_text) if salary_text else (None, None, "USD")

            # Get posted date
            date_el = await card.query_selector(
                "[data-cy='posted-date'], .card-posted-date, [class*='posted']"
            )
            posted_text = (await date_el.inner_text()).strip() if date_el else None
            posted_date = self._parse_posted_date(posted_text) if posted_text else None

            # Description snippet
            desc_el = await card.query_selector(
                "[data-cy='card-summary'], .card-description, [class*='summary']"
            )
            description = (await desc_el.inner_text()).strip() if desc_el else ""

            # Employment type
            type_el = await card.query_selector(
                "[data-cy='employment-type'], [class*='employment']"
            )
            job_type = (await type_el.inner_text()).strip().lower() if type_el else None

            # Skills/tags
            skills_els = await card.query_selector_all(
                "[data-cy='skill-tag'], .skill-tag, [class*='skill']"
            )
            requirements = []
            for skill_el in skills_els[:10]:  # Limit to 10 skills
                skill_text = (await skill_el.inner_text()).strip()
                if skill_text:
                    requirements.append(skill_text)

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
                posted_date=posted_date,
                posted_text=posted_text,
                job_type=job_type,
                requirements=requirements,
            )

        except Exception as e:
            logger.error(f"Error parsing Dice job card: {e}")
            return None

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        """Get full job details from listing page"""
        logger.debug(f"Fetching Dice job details: {url}")

        if not await self._navigate(url):
            return None

        # Wait for job description to load
        await self._wait_for_selector(
            "[data-cy='jobDescription'], #jobDescription, [class*='job-description']",
            timeout=15000
        )

        try:
            # Title
            title = await self._get_text(
                "[data-cy='job-title'], h1[class*='title'], .job-title"
            )

            # Company
            company_name = await self._get_text(
                "[data-cy='company-name-link'], a[class*='company'], .company-name"
            )

            # Location
            location = await self._get_text(
                "[data-cy='location'], [class*='job-location'], .location"
            )
            location_type = self._parse_location_type(location)

            # Remote check
            remote_el = await self._query_selector("[class*='remote-badge'], [data-cy*='remote']")
            if remote_el and not location_type:
                location_type = "remote"

            # Salary
            salary_text = await self._get_text(
                "[data-cy='compensation'], [class*='salary'], .compensation"
            )
            salary_min, salary_max, salary_currency = self._parse_salary(salary_text)

            # Full description
            description = await self._get_text(
                "[data-cy='jobDescription'], #jobDescription, [class*='job-description']"
            )
            description = self._clean_description(description)

            # Requirements/skills
            requirements = self._extract_requirements(description)

            # Additional skill tags
            skill_tags = await self._query_selector_all(
                "[data-cy='skill-tag'], .skill-tag, [class*='techSkill']"
            )
            for tag in skill_tags[:15]:
                skill = (await tag.inner_text()).strip()
                if skill and skill not in requirements:
                    requirements.append(skill)

            # Employment type
            job_type_el = await self._query_selector(
                "[data-cy='employment-type'], [class*='employment-type']"
            )
            job_type = (await job_type_el.inner_text()).strip().lower() if job_type_el else None

            # Posted date
            posted_text = await self._get_text(
                "[data-cy='posted-date'], [class*='posted'], .posted-date"
            )
            posted_date = self._parse_posted_date(posted_text) if posted_text else None

            # Company logo
            company_logo = await self._get_attribute(
                "img[data-cy='company-logo'], img[class*='company-logo']", "src"
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
                posted_date=posted_date,
                posted_text=posted_text,
                job_type=job_type,
                company_logo=company_logo,
            )

        except Exception as e:
            logger.error(f"Error getting Dice job details: {e}")
            return None
