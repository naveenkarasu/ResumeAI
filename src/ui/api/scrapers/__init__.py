"""Job scrapers module"""

from .base_scraper import (
    BaseScraper,
    ScrapedJob,
    register_scraper,
    get_scraper,
    get_all_scrapers,
)

# New async infrastructure
from .async_browser import (
    AsyncBrowserPool,
    get_browser_pool,
    close_browser_pool,
    fetch_with_browser,
    scroll_and_fetch,
)
from .proxy_pool import (
    ProxyPool,
    get_proxy_pool,
    get_random_proxy,
    close_proxy_pool,
)
from .orchestrator import (
    ScraperOrchestrator,
    OrchestratorResult,
    ScraperResult,
    search_jobs,
)
from .cache import (
    SearchCache,
    get_search_cache,
    get_cached_or_search,
)

# Import scrapers to register them
# HTTP-based scrapers (lightweight, recommended)
from .github_jobs_scraper import GitHubJobsScraper, SimplifyJobsScraper, JobrightScraper
from .http_scraper import RemoteOKScraper, HackerNewsJobsScraper, WeWorkRemotelyScraper
from .google_dorking_scraper import GoogleDorkScraper

# Browser-based scrapers (Playwright - use async_browser module)
from .indeed_scraper import IndeedScraper
from .ycombinator_scraper import YCombinatorScraper
from .builtin_scraper import BuiltInScraper
from .dice_scraper import DiceScraper
from .wellfound_scraper import WellfoundScraper

__all__ = [
    # Base classes
    "BaseScraper",
    "ScrapedJob",
    "register_scraper",
    "get_scraper",
    "get_all_scrapers",
    # New infrastructure
    "AsyncBrowserPool",
    "get_browser_pool",
    "close_browser_pool",
    "fetch_with_browser",
    "scroll_and_fetch",
    "ProxyPool",
    "get_proxy_pool",
    "get_random_proxy",
    "close_proxy_pool",
    "ScraperOrchestrator",
    "OrchestratorResult",
    "ScraperResult",
    "search_jobs",
    "SearchCache",
    "get_search_cache",
    "get_cached_or_search",
    # HTTP-based scrapers (recommended)
    "GitHubJobsScraper",
    "SimplifyJobsScraper",
    "JobrightScraper",
    "RemoteOKScraper",
    "HackerNewsJobsScraper",
    "WeWorkRemotelyScraper",
    "GoogleDorkScraper",
    # Browser-based scrapers
    "IndeedScraper",
    "YCombinatorScraper",
    "BuiltInScraper",
    "DiceScraper",
    "WellfoundScraper",
]
