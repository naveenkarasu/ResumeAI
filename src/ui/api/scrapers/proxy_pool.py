"""
Proxy Pool Management

Fetches, validates, and rotates free proxies for scraping.
Maintains a pool of working proxies with health checking.
"""

import asyncio
import httpx
import logging
import random
import time
from typing import Optional, List, Set, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class Proxy:
    """Represents a proxy server"""
    host: str
    port: int
    protocol: str = "http"
    country: Optional[str] = None
    anonymity: Optional[str] = None
    last_checked: Optional[datetime] = None
    response_time: Optional[float] = None
    fail_count: int = 0
    success_count: int = 0

    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def is_healthy(self) -> bool:
        """Check if proxy is considered healthy"""
        if self.fail_count >= 3:
            return False
        if self.response_time and self.response_time > 10:
            return False
        return True

    @property
    def score(self) -> float:
        """Calculate proxy quality score"""
        score = 100.0

        # Penalize failures
        score -= self.fail_count * 20

        # Reward successes
        score += min(self.success_count * 5, 30)

        # Penalize slow response
        if self.response_time:
            if self.response_time > 5:
                score -= 20
            elif self.response_time > 2:
                score -= 10

        return max(0, score)


# Free proxy list sources
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
]

# Test URL for proxy validation
TEST_URL = "https://httpbin.org/ip"


class ProxyPool:
    """
    Manages a pool of rotating proxies.

    Features:
    - Automatic proxy fetching from free lists
    - Health checking and validation
    - Smart rotation based on success/failure
    - Automatic refresh when pool runs low
    """

    def __init__(
        self,
        min_pool_size: int = 10,
        max_pool_size: int = 50,
        validation_timeout: float = 10.0,
        refresh_interval: int = 3600,  # 1 hour
    ):
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.validation_timeout = validation_timeout
        self.refresh_interval = refresh_interval

        self._proxies: Dict[str, Proxy] = {}
        self._blacklist: Set[str] = set()
        self._lock = asyncio.Lock()
        self._last_refresh: Optional[datetime] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._initialized = False

    async def initialize(self):
        """Initialize the proxy pool"""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            logger.info("Initializing proxy pool...")
            await self._fetch_proxies()
            await self._validate_proxies()
            self._initialized = True

            # Start background refresh
            self._refresh_task = asyncio.create_task(self._background_refresh())

    async def _fetch_proxies(self):
        """Fetch proxies from free proxy lists"""
        all_proxies: Set[str] = set()

        async with httpx.AsyncClient(timeout=30.0) as client:
            for source_url in PROXY_SOURCES:
                try:
                    response = await client.get(source_url)
                    if response.status_code == 200:
                        lines = response.text.strip().split("\n")
                        for line in lines:
                            line = line.strip()
                            if ":" in line and line not in self._blacklist:
                                all_proxies.add(line)
                        logger.debug(f"Fetched {len(lines)} proxies from {source_url}")
                except Exception as e:
                    logger.warning(f"Failed to fetch from {source_url}: {e}")

        # Parse and add proxies
        for proxy_str in list(all_proxies)[:200]:  # Limit to 200 for validation
            try:
                host, port = proxy_str.split(":")
                proxy = Proxy(host=host, port=int(port))
                self._proxies[proxy.url] = proxy
            except (ValueError, IndexError):
                continue

        logger.info(f"Fetched {len(self._proxies)} proxies for validation")
        self._last_refresh = datetime.now()

    async def _validate_proxy(self, proxy: Proxy) -> bool:
        """Validate a single proxy"""
        try:
            start_time = time.time()

            async with httpx.AsyncClient(
                proxy=proxy.url,
                timeout=self.validation_timeout,
            ) as client:
                response = await client.get(TEST_URL)

                if response.status_code == 200:
                    proxy.response_time = time.time() - start_time
                    proxy.last_checked = datetime.now()
                    proxy.success_count += 1
                    return True

        except Exception:
            proxy.fail_count += 1

        return False

    async def _validate_proxies(self, sample_size: int = 50):
        """Validate a sample of proxies concurrently"""
        proxies_to_check = list(self._proxies.values())[:sample_size]

        if not proxies_to_check:
            return

        logger.info(f"Validating {len(proxies_to_check)} proxies...")

        # Validate concurrently with limited parallelism
        semaphore = asyncio.Semaphore(10)

        async def validate_with_limit(proxy: Proxy):
            async with semaphore:
                return await self._validate_proxy(proxy)

        results = await asyncio.gather(
            *[validate_with_limit(p) for p in proxies_to_check],
            return_exceptions=True
        )

        valid_count = sum(1 for r in results if r is True)
        logger.info(f"Validated {valid_count}/{len(proxies_to_check)} proxies")

        # Remove failed proxies
        for proxy in proxies_to_check:
            if not proxy.is_healthy:
                self._blacklist.add(f"{proxy.host}:{proxy.port}")
                del self._proxies[proxy.url]

    async def _background_refresh(self):
        """Background task to refresh proxy pool"""
        while True:
            await asyncio.sleep(self.refresh_interval)

            try:
                # Check if refresh needed
                healthy_count = sum(1 for p in self._proxies.values() if p.is_healthy)

                if healthy_count < self.min_pool_size:
                    logger.info("Proxy pool running low, refreshing...")
                    await self._fetch_proxies()
                    await self._validate_proxies()

            except Exception as e:
                logger.error(f"Error in proxy refresh: {e}")

    async def get_proxy(self) -> Optional[str]:
        """
        Get a working proxy from the pool.

        Returns the highest-scoring healthy proxy.
        """
        if not self._initialized:
            await self.initialize()

        healthy_proxies = [p for p in self._proxies.values() if p.is_healthy]

        if not healthy_proxies:
            logger.warning("No healthy proxies available")
            return None

        # Sort by score and pick from top 5 randomly
        healthy_proxies.sort(key=lambda p: p.score, reverse=True)
        top_proxies = healthy_proxies[:min(5, len(healthy_proxies))]

        selected = random.choice(top_proxies)
        return selected.url

    async def get_proxies(self, count: int = 3) -> List[str]:
        """Get multiple proxies for parallel requests"""
        if not self._initialized:
            await self.initialize()

        healthy_proxies = [p for p in self._proxies.values() if p.is_healthy]
        healthy_proxies.sort(key=lambda p: p.score, reverse=True)

        selected = healthy_proxies[:min(count, len(healthy_proxies))]
        return [p.url for p in selected]

    def report_success(self, proxy_url: str):
        """Report successful use of a proxy"""
        if proxy_url in self._proxies:
            self._proxies[proxy_url].success_count += 1
            self._proxies[proxy_url].fail_count = max(0, self._proxies[proxy_url].fail_count - 1)

    def report_failure(self, proxy_url: str):
        """Report failed use of a proxy"""
        if proxy_url in self._proxies:
            self._proxies[proxy_url].fail_count += 1

            if not self._proxies[proxy_url].is_healthy:
                proxy = self._proxies[proxy_url]
                self._blacklist.add(f"{proxy.host}:{proxy.port}")
                del self._proxies[proxy_url]
                logger.debug(f"Removed unhealthy proxy: {proxy_url}")

    @property
    def pool_size(self) -> int:
        """Get current pool size"""
        return len(self._proxies)

    @property
    def healthy_count(self) -> int:
        """Get count of healthy proxies"""
        return sum(1 for p in self._proxies.values() if p.is_healthy)

    async def close(self):
        """Close the proxy pool"""
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass


# Global proxy pool instance
_proxy_pool: Optional[ProxyPool] = None


async def get_proxy_pool() -> ProxyPool:
    """Get or create the global proxy pool"""
    global _proxy_pool
    if _proxy_pool is None:
        _proxy_pool = ProxyPool()
    return _proxy_pool


async def get_random_proxy() -> Optional[str]:
    """Convenience function to get a random proxy"""
    pool = await get_proxy_pool()
    return await pool.get_proxy()


async def close_proxy_pool():
    """Close the global proxy pool"""
    global _proxy_pool
    if _proxy_pool:
        await _proxy_pool.close()
        _proxy_pool = None
