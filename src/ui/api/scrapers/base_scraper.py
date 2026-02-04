"""Base scraper framework for job sites"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, AsyncGenerator, Dict, Any
from datetime import datetime, date
import asyncio
import time
import random
import re
import logging
import hashlib

from .async_browser import get_browser_pool, AsyncBrowserPool

logger = logging.getLogger(__name__)


@dataclass
class ScrapedJob:
    """Standardized job data from scraping"""
    url: str
    title: str
    company_name: str
    description: str
    source: str

    # Optional fields
    location: Optional[str] = None
    location_type: Optional[str] = None  # remote/hybrid/onsite
    salary_text: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "USD"
    requirements: List[str] = field(default_factory=list)
    posted_date: Optional[date] = None
    posted_text: Optional[str] = None  # "2 days ago", etc.
    company_logo: Optional[str] = None
    company_website: Optional[str] = None
    company_industry: Optional[str] = None
    company_size: Optional[str] = None
    job_type: Optional[str] = None  # full-time, part-time, contract
    experience_level: Optional[str] = None  # entry, mid, senior, lead

    # Metadata
    scraped_at: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for database insertion"""
        # Handle posted_date - might be date object or already a string
        posted_date_str = None
        if self.posted_date:
            if isinstance(self.posted_date, str):
                posted_date_str = self.posted_date
            else:
                posted_date_str = self.posted_date.isoformat()

        return {
            "url": self.url,
            "title": self.title,
            "company_name": self.company_name,
            "description": self.description,
            "source": self.source,
            "location": self.location,
            "location_type": self.location_type,
            "salary_text": self.salary_text,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_currency": self.salary_currency,
            "requirements": self.requirements,
            "posted_date": posted_date_str,
            "company_logo": self.company_logo,
            "company_website": self.company_website,
            "company_industry": self.company_industry,
            "company_size": self.company_size,
        }

    @property
    def content_hash(self) -> str:
        """Generate hash for deduplication"""
        content = f"{self.title}|{self.company_name}|{self.location}".lower()
        return hashlib.md5(content.encode()).hexdigest()[:16]


class BaseScraper(ABC):
    """
    Abstract base class for job site scrapers.

    Implements rate limiting, error handling, and common utilities.
    Subclasses must implement search() and get_job_details().
    """

    # Configuration - override in subclasses
    RATE_LIMIT_SECONDS = 5      # Min seconds between requests
    MAX_PAGES = 10              # Max pages to scrape per search
    MAX_RETRIES = 3             # Max retries on failure
    TIMEOUT_SECONDS = 30        # Request timeout
    RESPECT_ROBOTS_TXT = True   # Check robots.txt

    def __init__(self):
        self.last_request_time = 0
        self._browser = None
        self._browser_pool = None
        self._page = None
        self._context = None

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the source identifier (e.g., 'linkedin', 'indeed')"""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the base URL for the job site"""
        pass

    @abstractmethod
    async def search(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        filters: Optional[Dict] = None
    ) -> AsyncGenerator[ScrapedJob, None]:
        """
        Search for jobs and yield results.

        Args:
            keywords: Search terms (job titles, skills, etc.)
            location: Location filter (city, state, "remote", etc.)
            filters: Additional filters (salary, job type, etc.)

        Yields:
            ScrapedJob objects for each found job
        """
        pass

    @abstractmethod
    async def get_job_details(self, url: str) -> Optional[ScrapedJob]:
        """
        Get full details for a specific job listing.

        Args:
            url: The job listing URL

        Returns:
            ScrapedJob with full details, or None if not found
        """
        pass

    # ============== Browser Management ==============

    async def _init_browser(self):
        """Initialize async Playwright browser via the browser pool"""
        if self._page is not None:
            return

        try:
            # Get the global browser pool
            pool = await get_browser_pool()

            # Create a new context from the pool
            self._browser_pool = pool
            await pool._ensure_browser()
            self._browser = pool._browser

            # Create context with stealth settings
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
            )

            # Add stealth scripts
            await self._context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                window.chrome = { runtime: {} };
            """)

            self._page = await self._context.new_page()
            self._page.set_default_timeout(self.TIMEOUT_SECONDS * 1000)

            logger.info(f"Async browser initialized for {self.source_name}")

        except NotImplementedError as e:
            # Windows asyncio subprocess limitation with uvicorn
            logger.error(
                f"Browser initialization failed for {self.source_name}: {e}. "
                f"This is a known Windows limitation with Playwright + uvicorn. "
                f"Browser-based scrapers are disabled."
            )
            raise RuntimeError(f"Browser scrapers not available on this platform: {e}")

        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    async def _close_browser(self):
        """Close browser context and cleanup"""
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
        except Exception as e:
            logger.debug(f"Error closing browser: {e}")
        finally:
            self._page = None
            self._context = None
            self._browser = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self._init_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._close_browser()

    # ============== Rate Limiting ==============

    async def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_SECONDS:
            wait_time = self.RATE_LIMIT_SECONDS - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
        self.last_request_time = time.time()

    async def _random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Add random delay to appear more human"""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def _human_scroll(self, page=None):
        """Simulate human-like scrolling"""
        page = page or self._page
        if not page:
            return

        # Scroll down in random increments
        scroll_distance = random.randint(300, 700)
        await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
        await asyncio.sleep(random.uniform(0.3, 0.8))

    # ============== Navigation Helpers ==============

    async def _navigate(self, url: str, wait_for: str = "networkidle") -> bool:
        """
        Navigate to URL with rate limiting and error handling.

        Args:
            url: URL to navigate to
            wait_for: Playwright wait condition

        Returns:
            True if successful, False otherwise
        """
        await self._rate_limit()

        try:
            response = await self._page.goto(
                url,
                wait_until=wait_for,
                timeout=self.TIMEOUT_SECONDS * 1000
            )

            if response and response.status >= 400:
                logger.warning(f"HTTP {response.status} for {url}")
                return False

            await self._random_delay(0.5, 1.5)
            return True

        except Exception as e:
            logger.error(f"Navigation failed for {url}: {e}")
            return False

    async def _wait_for_selector(self, selector: str, timeout: int = 10000) -> bool:
        """Wait for element with timeout"""
        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False

    async def _get_text(self, selector: str, default: str = "") -> str:
        """Safely get text content from selector"""
        try:
            element = await self._page.query_selector(selector)
            if element:
                return (await element.inner_text()).strip()
        except Exception:
            pass
        return default

    async def _get_attribute(self, selector: str, attr: str, default: str = "") -> str:
        """Safely get attribute from selector"""
        try:
            element = await self._page.query_selector(selector)
            if element:
                value = await element.get_attribute(attr)
                return value.strip() if value else default
        except Exception:
            pass
        return default

    async def _get_all_text(self, selector: str) -> List[str]:
        """Get text from all matching elements"""
        try:
            elements = await self._page.query_selector_all(selector)
            texts = []
            for el in elements:
                text = (await el.inner_text()).strip()
                if text:
                    texts.append(text)
            return texts
        except Exception:
            return []

    async def _query_selector(self, selector: str):
        """Query single element"""
        try:
            return await self._page.query_selector(selector)
        except Exception:
            return None

    async def _query_selector_all(self, selector: str) -> List:
        """Query all matching elements"""
        try:
            return await self._page.query_selector_all(selector)
        except Exception:
            return []

    async def _element_inner_text(self, element) -> str:
        """Get inner text from element"""
        try:
            return (await element.inner_text()).strip() if element else ""
        except Exception:
            return ""

    async def _element_get_attribute(self, element, attr: str) -> Optional[str]:
        """Get attribute from element"""
        try:
            value = await element.get_attribute(attr) if element else None
            return value.strip() if value else None
        except Exception:
            return None

    async def _element_evaluate(self, element, expression: str):
        """Evaluate JS expression on element"""
        try:
            return await element.evaluate(expression) if element else None
        except Exception:
            return None

    async def _element_query_selector(self, element, selector: str):
        """Query selector on element"""
        try:
            return await element.query_selector(selector) if element else None
        except Exception:
            return None

    # ============== Parsing Utilities ==============

    def _parse_salary(self, salary_text: str) -> tuple[Optional[int], Optional[int], str]:
        """
        Parse salary text into min, max, and currency.

        Args:
            salary_text: Raw salary string (e.g., "$120K - $180K", "150,000 - 200,000 USD")

        Returns:
            Tuple of (salary_min, salary_max, currency)
        """
        if not salary_text:
            return None, None, "USD"

        salary_text = salary_text.upper().replace(",", "").replace(" ", "")

        # Detect currency
        currency = "USD"
        if "£" in salary_text or "GBP" in salary_text:
            currency = "GBP"
        elif "€" in salary_text or "EUR" in salary_text:
            currency = "EUR"
        elif "CAD" in salary_text:
            currency = "CAD"

        # Extract numbers
        numbers = re.findall(r"(\d+(?:\.\d+)?)[K]?", salary_text)

        if not numbers:
            return None, None, currency

        # Convert K notation
        values = []
        for num in numbers:
            value = float(num)
            # Check if K notation was used
            if f"{num}K" in salary_text or value < 1000:
                value *= 1000
            values.append(int(value))

        if len(values) == 1:
            return values[0], values[0], currency
        elif len(values) >= 2:
            return min(values), max(values), currency

        return None, None, currency

    def _parse_location_type(self, text: str) -> Optional[str]:
        """Parse location type from text"""
        if not text:
            return None

        text_lower = text.lower()

        if "remote" in text_lower:
            if "hybrid" in text_lower:
                return "hybrid"
            return "remote"
        elif "hybrid" in text_lower:
            return "hybrid"
        elif "on-site" in text_lower or "onsite" in text_lower or "in-office" in text_lower:
            return "onsite"

        return None

    def _parse_posted_date(self, text: str) -> Optional[date]:
        """
        Parse relative date text into actual date.

        Args:
            text: Relative date string (e.g., "2 days ago", "1 week ago", "Just posted")

        Returns:
            Parsed date or None
        """
        if not text:
            return None

        text_lower = text.lower().strip()
        today = date.today()

        # Just posted / today
        if any(x in text_lower for x in ["just", "today", "now", "< 24"]):
            return today

        # Yesterday
        if "yesterday" in text_lower:
            return date.fromordinal(today.toordinal() - 1)

        # X days ago
        days_match = re.search(r"(\d+)\s*days?\s*ago", text_lower)
        if days_match:
            days = int(days_match.group(1))
            return date.fromordinal(today.toordinal() - days)

        # X weeks ago
        weeks_match = re.search(r"(\d+)\s*weeks?\s*ago", text_lower)
        if weeks_match:
            weeks = int(weeks_match.group(1))
            return date.fromordinal(today.toordinal() - (weeks * 7))

        # X months ago
        months_match = re.search(r"(\d+)\s*months?\s*ago", text_lower)
        if months_match:
            months = int(months_match.group(1))
            return date.fromordinal(today.toordinal() - (months * 30))

        # Try to parse actual date
        date_formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"]
        for fmt in date_formats:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue

        return None

    def _extract_requirements(self, description: str) -> List[str]:
        """Extract requirements/skills from job description"""
        requirements = []

        # Common requirement section headers
        req_patterns = [
            r"(?:requirements?|qualifications?|what you.?ll need|must have)[:\s]*\n((?:[-•*]\s*.+\n?)+)",
            r"(?:skills?|technologies?|tech stack)[:\s]*\n((?:[-•*]\s*.+\n?)+)",
        ]

        for pattern in req_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            for match in matches:
                # Extract bullet points
                bullets = re.findall(r"[-•*]\s*(.+?)(?:\n|$)", match)
                requirements.extend([b.strip() for b in bullets if len(b.strip()) > 3])

        # Also extract common skills mentioned
        skill_keywords = [
            "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
            "React", "Vue", "Angular", "Node.js", "Django", "FastAPI", "Flask",
            "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform",
            "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
            "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
            "CI/CD", "Git", "Agile", "Scrum"
        ]

        desc_lower = description.lower()
        for skill in skill_keywords:
            if skill.lower() in desc_lower and skill not in requirements:
                requirements.append(skill)

        return list(set(requirements))[:20]  # Limit to 20 unique items

    def _clean_description(self, description: str) -> str:
        """Clean and normalize job description text"""
        if not description:
            return ""

        # Remove excessive whitespace
        description = re.sub(r"\s+", " ", description)

        # Remove HTML entities
        description = re.sub(r"&\w+;", " ", description)

        # Normalize line breaks
        description = re.sub(r"\n{3,}", "\n\n", description)

        return description.strip()

    # ============== Error Handling ==============

    async def _retry_operation(self, operation, *args, **kwargs):
        """Retry an operation with exponential backoff"""
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_error = e
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Attempt {attempt + 1}/{self.MAX_RETRIES} failed for {self.source_name}: {e}. "
                    f"Retrying in {wait_time:.1f}s"
                )
                await asyncio.sleep(wait_time)

        raise last_error


# ============== Scraper Registry ==============

_scraper_registry: Dict[str, type] = {}


def register_scraper(source_name: str):
    """Decorator to register a scraper class"""
    def decorator(cls):
        _scraper_registry[source_name] = cls
        return cls
    return decorator


def get_scraper(source_name: str) -> Optional[type]:
    """Get scraper class by source name"""
    return _scraper_registry.get(source_name)


def get_all_scrapers() -> Dict[str, type]:
    """Get all registered scrapers"""
    return _scraper_registry.copy()
