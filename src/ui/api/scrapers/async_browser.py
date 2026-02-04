"""
Async Browser Management for Playwright

Uses playwright.async_api to avoid greenlet/threading issues that occur
when using sync_playwright with asyncio.to_thread().
"""

import asyncio
import logging
import random
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Realistic user agents pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

# Viewport sizes for fingerprint variation
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
]

# Timezones for variation
TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Toronto",
]


@dataclass
class BrowserConfig:
    """Configuration for browser instances"""
    headless: bool = True
    timeout: int = 30000  # 30 seconds
    proxy: Optional[str] = None
    user_agent: Optional[str] = None
    viewport: Optional[Dict[str, int]] = None
    timezone: Optional[str] = None
    locale: str = "en-US"


class AsyncBrowserPool:
    """
    Manages a pool of async Playwright browser contexts.

    Features:
    - Single browser instance with multiple contexts
    - Fingerprint randomization per context
    - Auto-cleanup on idle
    - Proxy support
    """

    def __init__(self, max_contexts: int = 3):
        self.max_contexts = max_contexts
        self._playwright = None
        self._browser = None
        self._contexts: List[Any] = []
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._last_used = 0

    async def _ensure_browser(self):
        """Ensure browser is initialized"""
        if self._browser is None:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-infobars",
                    "--window-size=1920,1080",
                ]
            )
            logger.info("Async Playwright browser initialized")

            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._auto_cleanup())

    async def _auto_cleanup(self):
        """Auto-close browser after 5 minutes of inactivity"""
        while True:
            await asyncio.sleep(60)  # Check every minute
            if self._browser and (asyncio.get_event_loop().time() - self._last_used) > 300:
                logger.info("Auto-closing idle browser")
                await self.close()
                break

    def _get_random_config(self, proxy: Optional[str] = None) -> BrowserConfig:
        """Generate randomized browser config for fingerprint variation"""
        return BrowserConfig(
            headless=True,
            proxy=proxy,
            user_agent=random.choice(USER_AGENTS),
            viewport=random.choice(VIEWPORTS),
            timezone=random.choice(TIMEZONES),
            locale="en-US",
        )

    @asynccontextmanager
    async def get_context(self, config: Optional[BrowserConfig] = None, proxy: Optional[str] = None):
        """
        Get a browser context with stealth settings.

        Usage:
            async with pool.get_context() as context:
                page = await context.new_page()
                await page.goto(url)
        """
        async with self._lock:
            await self._ensure_browser()

        if config is None:
            config = self._get_random_config(proxy)

        # Build context options
        context_options = {
            "viewport": config.viewport or {"width": 1920, "height": 1080},
            "user_agent": config.user_agent or random.choice(USER_AGENTS),
            "locale": config.locale,
            "timezone_id": config.timezone or random.choice(TIMEZONES),
            "permissions": ["geolocation"],
            "geolocation": {"latitude": 40.7128, "longitude": -74.0060},  # NYC
            "color_scheme": "light",
        }

        if config.proxy:
            context_options["proxy"] = {"server": config.proxy}

        context = await self._browser.new_context(**context_options)

        # Add stealth scripts to all pages
        await context.add_init_script("""
            // Override webdriver detection
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // Add chrome object
            window.chrome = { runtime: {} };

            // Override iframe contentWindow
            const originalContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
            Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                get: function() {
                    const win = originalContentWindow.get.call(this);
                    if (win) {
                        Object.defineProperty(win.navigator, 'webdriver', { get: () => undefined });
                    }
                    return win;
                }
            });
        """)

        self._last_used = asyncio.get_event_loop().time()

        try:
            yield context
        finally:
            await context.close()

    @asynccontextmanager
    async def get_page(self, config: Optional[BrowserConfig] = None, proxy: Optional[str] = None):
        """
        Get a new page with stealth settings.

        Usage:
            async with pool.get_page() as page:
                await page.goto(url)
                content = await page.content()
        """
        async with self.get_context(config, proxy) as context:
            page = await context.new_page()

            # Set default timeout
            page.set_default_timeout(30000)

            try:
                yield page
            finally:
                await page.close()

    async def close(self):
        """Close browser and cleanup"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        logger.info("Async browser pool closed")


# Global browser pool instance
_browser_pool: Optional[AsyncBrowserPool] = None


async def get_browser_pool() -> AsyncBrowserPool:
    """Get or create the global browser pool"""
    global _browser_pool
    if _browser_pool is None:
        _browser_pool = AsyncBrowserPool()
    return _browser_pool


async def close_browser_pool():
    """Close the global browser pool"""
    global _browser_pool
    if _browser_pool:
        await _browser_pool.close()
        _browser_pool = None


# Helper functions for common operations

async def fetch_with_browser(
    url: str,
    wait_selector: Optional[str] = None,
    proxy: Optional[str] = None,
    timeout: int = 30000,
) -> Optional[str]:
    """
    Fetch a page using Playwright and return HTML content.

    Args:
        url: URL to fetch
        wait_selector: Optional CSS selector to wait for
        proxy: Optional proxy URL
        timeout: Timeout in milliseconds

    Returns:
        HTML content or None on failure
    """
    pool = await get_browser_pool()

    try:
        async with pool.get_page(proxy=proxy) as page:
            page.set_default_timeout(timeout)

            response = await page.goto(url, wait_until="networkidle")

            if response and response.status >= 400:
                logger.warning(f"HTTP {response.status} for {url}")
                return None

            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=10000)
                except Exception:
                    logger.debug(f"Selector {wait_selector} not found, continuing")

            # Random delay to appear human
            await asyncio.sleep(random.uniform(0.5, 1.5))

            return await page.content()

    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


async def scroll_and_fetch(
    url: str,
    scroll_count: int = 3,
    wait_selector: Optional[str] = None,
    proxy: Optional[str] = None,
) -> Optional[str]:
    """
    Fetch a page with scrolling to load lazy content.

    Args:
        url: URL to fetch
        scroll_count: Number of times to scroll
        wait_selector: Optional selector to wait for
        proxy: Optional proxy URL

    Returns:
        HTML content or None on failure
    """
    pool = await get_browser_pool()

    try:
        async with pool.get_page(proxy=proxy) as page:
            response = await page.goto(url, wait_until="networkidle")

            if response and response.status >= 400:
                return None

            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=10000)
                except Exception:
                    pass

            # Scroll to load lazy content
            for _ in range(scroll_count):
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(random.uniform(0.3, 0.8))

            # Scroll back to top
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(random.uniform(0.5, 1.0))

            return await page.content()

    except Exception as e:
        logger.error(f"Failed to fetch {url} with scrolling: {e}")
        return None
