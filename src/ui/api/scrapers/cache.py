"""
Search Result Cache

Provides caching for job search results with configurable TTL.
Supports both Redis (production) and in-memory (development) backends.
"""

import asyncio
import json
import logging
import hashlib
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import os

from .base_scraper import ScrapedJob

logger = logging.getLogger(__name__)

# Default cache TTL: 6 hours
DEFAULT_TTL = 6 * 60 * 60


@dataclass
class CachedResult:
    """Cached search result"""
    jobs: List[Dict[str, Any]]
    total_found: int
    sources_succeeded: List[str]
    sources_failed: List[str]
    cached_at: str
    expires_at: str

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "CachedResult":
        return cls(**json.loads(data))

    def is_expired(self) -> bool:
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now() > expires


class CacheBackend(ABC):
    """Abstract cache backend"""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int) -> bool:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def clear(self) -> bool:
        pass


class InMemoryCache(CacheBackend):
    """
    Simple in-memory cache for development.

    Not suitable for production with multiple workers.
    """

    def __init__(self):
        self._cache: Dict[str, tuple[str, datetime]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            if key in self._cache:
                value, expires = self._cache[key]
                if datetime.now() < expires:
                    return value
                else:
                    del self._cache[key]
            return None

    async def set(self, key: str, value: str, ttl: int) -> bool:
        async with self._lock:
            expires = datetime.now() + timedelta(seconds=ttl)
            self._cache[key] = (value, expires)
            return True

    async def delete(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> bool:
        async with self._lock:
            self._cache.clear()
            return True

    async def cleanup_expired(self):
        """Remove expired entries"""
        async with self._lock:
            now = datetime.now()
            expired = [k for k, (_, exp) in self._cache.items() if now >= exp]
            for key in expired:
                del self._cache[key]


class RedisCache(CacheBackend):
    """
    Redis-based cache for production.

    Requires redis package: pip install redis
    """

    def __init__(self, url: Optional[str] = None):
        self.url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(self.url)
            except ImportError:
                logger.warning("Redis package not installed, falling back to in-memory cache")
                raise
        return self._client

    async def get(self, key: str) -> Optional[str]:
        try:
            client = await self._get_client()
            value = await client.get(f"scraper:{key}")
            return value.decode() if value else None
        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int) -> bool:
        try:
            client = await self._get_client()
            await client.setex(f"scraper:{key}", ttl, value)
            return True
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        try:
            client = await self._get_client()
            await client.delete(f"scraper:{key}")
            return True
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")
            return False

    async def clear(self) -> bool:
        try:
            client = await self._get_client()
            keys = await client.keys("scraper:*")
            if keys:
                await client.delete(*keys)
            return True
        except Exception as e:
            logger.warning(f"Redis clear error: {e}")
            return False


class SearchCache:
    """
    High-level search result cache.

    Automatically selects backend based on environment.
    """

    def __init__(self, ttl: int = DEFAULT_TTL, backend: Optional[CacheBackend] = None):
        self.ttl = ttl

        if backend:
            self._backend = backend
        elif os.getenv("REDIS_URL"):
            try:
                self._backend = RedisCache()
            except Exception:
                self._backend = InMemoryCache()
        else:
            self._backend = InMemoryCache()

        logger.info(f"Search cache initialized with {type(self._backend).__name__}")

    def _generate_key(
        self,
        keywords: List[str],
        location: Optional[str],
        filters: Optional[Dict],
    ) -> str:
        """Generate cache key from search parameters"""
        key_parts = [
            ":".join(sorted(k.lower() for k in keywords)) if keywords else "",
            (location or "").lower(),
            hashlib.md5(
                json.dumps(filters, sort_keys=True).encode() if filters else b""
            ).hexdigest()[:8],
        ]
        return hashlib.md5(":".join(key_parts).encode()).hexdigest()[:16]

    async def get(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        filters: Optional[Dict] = None,
    ) -> Optional[CachedResult]:
        """
        Get cached search results.

        Returns None if not cached or expired.
        """
        key = self._generate_key(keywords, location, filters)

        cached = await self._backend.get(key)
        if cached:
            try:
                result = CachedResult.from_json(cached)
                if not result.is_expired():
                    logger.debug(f"Cache hit for key {key}")
                    return result
                else:
                    await self._backend.delete(key)
            except Exception as e:
                logger.warning(f"Error parsing cached result: {e}")
                await self._backend.delete(key)

        return None

    async def set(
        self,
        keywords: List[str],
        location: Optional[str],
        filters: Optional[Dict],
        jobs: List[ScrapedJob],
        sources_succeeded: List[str],
        sources_failed: List[str],
    ) -> bool:
        """Cache search results"""
        key = self._generate_key(keywords, location, filters)

        now = datetime.now()
        expires = now + timedelta(seconds=self.ttl)

        result = CachedResult(
            jobs=[j.to_dict() for j in jobs],
            total_found=len(jobs),
            sources_succeeded=sources_succeeded,
            sources_failed=sources_failed,
            cached_at=now.isoformat(),
            expires_at=expires.isoformat(),
        )

        success = await self._backend.set(key, result.to_json(), self.ttl)
        if success:
            logger.debug(f"Cached {len(jobs)} jobs with key {key}")
        return success

    async def invalidate(
        self,
        keywords: List[str],
        location: Optional[str] = None,
        filters: Optional[Dict] = None,
    ) -> bool:
        """Invalidate cached results for specific search"""
        key = self._generate_key(keywords, location, filters)
        return await self._backend.delete(key)

    async def clear_all(self) -> bool:
        """Clear all cached results"""
        return await self._backend.clear()


# Global cache instance
_search_cache: Optional[SearchCache] = None


def get_search_cache(ttl: int = DEFAULT_TTL) -> SearchCache:
    """Get or create the global search cache"""
    global _search_cache
    if _search_cache is None:
        _search_cache = SearchCache(ttl=ttl)
    return _search_cache


async def get_cached_or_search(
    keywords: List[str],
    location: Optional[str] = None,
    filters: Optional[Dict] = None,
    sources: Optional[List[str]] = None,
    force_refresh: bool = False,
):
    """
    Get cached results or perform fresh search.

    This is the main entry point that combines caching with searching.
    """
    from .orchestrator import search_jobs, OrchestratorResult

    cache = get_search_cache()

    # Check cache first (unless force refresh)
    if not force_refresh:
        cached = await cache.get(keywords, location, filters)
        if cached:
            # Convert cached data back to ScrapedJob objects
            jobs = [ScrapedJob(**j) for j in cached.jobs]
            return OrchestratorResult(
                jobs=jobs,
                total_found=cached.total_found,
                sources_succeeded=cached.sources_succeeded,
                sources_failed=cached.sources_failed,
                sources_partial=[],
                duration_ms=0,
                cached=True,
            )

    # Perform fresh search
    result = await search_jobs(keywords, location, filters, sources)

    # Cache the results
    if result.jobs:
        await cache.set(
            keywords,
            location,
            filters,
            result.jobs,
            result.sources_succeeded,
            result.sources_failed,
        )

    return result
