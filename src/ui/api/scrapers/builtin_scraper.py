"""BuiltIn job scraper"""

from typing import List, Optional, AsyncGenerator, Dict
from datetime import date
import re
import logging
import asyncio

from .base_scraper import BaseScraper, ScrapedJob, register_scraper

logger = logging.getLogger(__name__)


@register_scraper("builtin")
class BuiltInScraper(BaseScraper):
    """
    Scraper for BuiltIn.com job listings.

    BuiltIn focuses on tech companies and startups, organized by city/region.
    They have separate sites for different cities (builtinnyc, builtinla, etc.)
    but also a main site with all listings.

    URL: https://builtin.com/jobs
    """

    RATE_LIMIT_SECONDS = 4
    MAX_PAGES = 8

    @property
    def source_name(self) -> str:
        return "builtin"

    @property
    def base_url(self) -> str:
        return "https://builtin.com"

    def _get_location_subdomain(self, location: Optional[str]) -> str:
        """Get BuiltIn subdomain for location"""
        if not location:
            return self.base_url

        location_lower = location.lower()

        # BuiltIn city-specific domains
        location_map = {
            "new york": "https://www.builtinnyc.com",
            "nyc": "https://www.builtinnyc.com",
            "los angeles": "https://www.builtinla.com",
            "la": "https://www.builtinla.com",
            "chicago": "https://www.builtinchicago.com",
            "boston": "https://www.builtinboston.com",
            "colorado": "https://www.builtincolorado.com",
            "denver": "https://www.builtincolorado.com",
            "seattle": "https://www.builtinseattle.com",
            "san francisco": "https://www.builtinsf.com",
            "sf": "https://www.builtinsf.com",
            "austin": "https://www.builtinaustin.com",
        }

        for key, domain in location_map.items():
            if key in location_lower:
                return domain

        return self.base_url

    def _build_search_url(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        page: int = 1,
        filters: Optional[Dict] = None
    ) -> str:
        """Build BuiltIn search URL"""
        base = self._get_location_subdomain(location)
        url = f"{base}/jobs"

        params = []

        if keywords:
            query = " ".join(keywords)
            params.append(f"search={query.replace(' ', '%20')}")

        if filters:
            # Remote filter
            if filters.get("remote") or (location and location.lower() == "remote"):
                params.append("remote=true")

            # Experience level
            if filters.get("experience_level"):
                exp_map = {
                    "entry": "entry",
                    "mid": "mid-level",
                    "senior": "senior",
                    "lead": "manager",
                    "executive": "director"
                }
                if filters["experience_level"] in exp_map:
                    params.append(f"experience={exp_map[filters['experience_level']]}")

            # Company size
            if filters.get("company_size"):
                size_map = {
                    "startup": "1-10,11-50",
                    "small": "51-200",
                    "medium": "201-500,501-1000",
                    "large": "1001-5000",
                    "enterprise": "5001%2B"
                }
                if filters["company_size"] in size_map:
                    params.append(f"company_size={size_map[filters['company_size']]}")

            # Industry
            if filters.get("industry"):
                params.append(f"industry={filters['industry'].replace(' ', '%20')}")

            # Job category
            if filters.get("category"):
                params.append(f"category={filters['category'].replace(' ', '%20')}")

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
        """Search BuiltIn for jobs"""
        filters = filters or {}
        page = 1

        logger.info(f"Starting BuiltIn search: keywords={keywords}, location={location}")

        while page <= self.MAX_PAGES:
            url = self._build_search_url(keywords, location, page, filters)

            logger.debug(f"Scraping BuiltIn page {page}: {url}")

            if not await self._navigate(url):
                logger.warning(f"Failed to navigate to BuiltIn search page {page}")
                break

            # Wait for job cards to load
            await self._wait_for_selector("[data-id='job-card'], .job-card, [class*='JobCard']", timeout=10000)

            # Scroll to load lazy content
            for _ in range(4):
                await self._human_scroll()
                await self._random_delay(0.5, 1.0)

            # Extract job cards
            job_cards = await self._query_selector_all(
                "[data-id='job-card'], .job-card, [class*='JobCard'], article[class*='job']"
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
                    logger.warning(f"Failed to parse BuiltIn job card: {e}")
                    continue

            logger.info(f"Found {jobs_found} jobs on BuiltIn page {page}")

            if jobs_found < 5:  # Probably last page
                break

            page += 1
            await self._random_delay(2, 4)

    async def _parse_job_card(self, card) -> Optional[ScrapedJob]:
        """Parse a job card element into ScrapedJob (async)"""
        try:
            # Get job title and URL
            title_el = await card.query_selector(
                "a[data-id='job-title'], h2 a, h3 a, [class*='title'] a, a[class*='job-title']"
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
                "[data-id='company-title'], [class*='company'], a[href*='/company/']"
            )
            company_name = (await company_el.inner_text()).strip() if company_el else "Unknown"

            # Get location
            location_el = await card.query_selector(
                "[data-id='job-location'], [class*='location'], span[class*='Location']"
            )
            location = (await location_el.inner_text()).strip() if location_el else None
            location_type = self._parse_location_type(location) if location else None

            # Remote badge
            remote_badge = await card.query_selector("[class*='remote'], [data-id*='remote']")
            if remote_badge and not location_type:
                remote_text = await remote_badge.inner_text()
                if "remote" in remote_text.lower():
                    location_type = "remote"

            # Get salary
            salary_el = await card.query_selector(
                "[data-id='salary'], [class*='salary'], [class*='compensation']"
            )
            salary_text = (await salary_el.inner_text()).strip() if salary_el else None
            salary_min, salary_max, salary_currency = self._parse_salary(salary_text) if salary_text else (None, None, "USD")

            # Get posted date
            date_el = await card.query_selector("[class*='date'], time, [data-id='posted']")
            posted_text = None
            posted_date = None
            if date_el:
                posted_text = (await date_el.inner_text()).strip()
                # Also try datetime attribute
                datetime_attr = await date_el.get_attribute("datetime")
                if datetime_attr:
                    try:
                        posted_date = date.fromisoformat(datetime_attr[:10])
                    except ValueError:
                        posted_date = self._parse_posted_date(posted_text)
                else:
                    posted_date = self._parse_posted_date(posted_text)

            # Company logo
            logo_el = await card.query_selector("img[src*='logo'], img[class*='logo'], img[class*='company']")
            company_logo = await logo_el.get_attribute("src") if logo_el else None

            # Description snippet
            desc_el = await card.query_selector("[class*='description'], p[class*='snippet']")
            description = (await desc_el.inner_text()).strip() if desc_el else ""

            # Company size info
            size_el = await card.query_selector("[class*='company-size'], [data-id='company-size']")
            company_size = None
            if size_el:
                size_text = (await size_el.inner_text()).strip().lower()
                if any(x in size_text for x in ["1-10", "11-50", "1 - 50"]):
                    company_size = "startup"
                elif any(x in size_text for x in ["51-200", "51 - 200"]):
                    company_size = "small"
                elif any(x in size_text for x in ["201-500", "501-1000"]):
                    company_size = "medium"
                elif any(x in size_text for x in ["1001-5000", "1,001-5,000"]):
                    company_size = "large"
                elif "5000" in size_text or "5,000" in size_text:
                    company_size = "enterprise"

            # Industry
            industry_el = await card.query_selector("[class*='industry'], [data-id='industry']")
            industry = (await industry_el.inner_text()).strip() if industry_el else None

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
                company_logo=company_logo,
                company_size=company_size,
                company_industry=industry,
            )

        except Exception as e:
            logger.error(f"Error parsing BuiltIn job card: {e}")
            return None

    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        """Get full job details from listing page"""
        logger.debug(f"Fetching BuiltIn job details: {url}")

        if not await self._navigate(url):
            return None

        # Wait for job description
        await self._wait_for_selector("[class*='job-description'], [data-id='job-description'], main", timeout=10000)

        try:
            # Title
            title = await self._get_text("h1, [data-id='job-title'], [class*='job-title']")

            # Company
            company_name = await self._get_text(
                "[data-id='company-name'], [class*='company-name'], a[href*='/company/'] > span"
            )

            # Location
            location = await self._get_text("[data-id='job-location'], [class*='job-location']")
            location_type = self._parse_location_type(location)

            # Salary
            salary_text = await self._get_text("[data-id='job-salary'], [class*='salary'], [class*='compensation']")
            salary_min, salary_max, salary_currency = self._parse_salary(salary_text)

            # Full description
            description = await self._get_text(
                "[data-id='job-description'], [class*='job-description'], article"
            )
            description = self._clean_description(description)

            # Requirements
            requirements = self._extract_requirements(description)

            # Additional job details
            job_type_el = await self._query_selector("[class*='job-type'], [data-id='job-type']")
            job_type = (await job_type_el.inner_text()).strip().lower() if job_type_el else None

            experience_el = await self._query_selector("[class*='experience'], [data-id='experience']")
            experience_level = None
            if experience_el:
                exp_text = (await experience_el.inner_text()).strip().lower()
                if any(x in exp_text for x in ["entry", "junior", "0-2"]):
                    experience_level = "entry"
                elif any(x in exp_text for x in ["mid", "3-5", "intermediate"]):
                    experience_level = "mid"
                elif any(x in exp_text for x in ["senior", "5+", "lead"]):
                    experience_level = "senior"

            # Company info
            company_logo = await self._get_attribute("img[class*='company-logo'], img[class*='logo']", "src")
            company_website = await self._get_attribute("a[class*='company-website'], a[class*='website']", "href")
            company_industry = await self._get_text("[class*='company-industry'], [data-id='industry']")

            # Company size
            size_text = await self._get_text("[class*='company-size'], [data-id='company-size']")
            company_size = None
            if size_text:
                size_lower = size_text.lower()
                if any(x in size_lower for x in ["1-50", "startup"]):
                    company_size = "startup"
                elif "51-200" in size_lower:
                    company_size = "small"
                elif any(x in size_lower for x in ["201-500", "501-1000"]):
                    company_size = "medium"
                elif "1001-5000" in size_lower:
                    company_size = "large"
                elif "5000" in size_lower:
                    company_size = "enterprise"

            # Posted date
            posted_text = await self._get_text("[class*='posted'], time[class*='date']")
            posted_date = self._parse_posted_date(posted_text) if posted_text else None

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
                company_logo=company_logo,
                company_website=company_website,
                company_industry=company_industry,
                company_size=company_size,
                job_type=job_type,
                experience_level=experience_level,
            )

        except Exception as e:
            logger.error(f"Error getting BuiltIn job details: {e}")
            return None
