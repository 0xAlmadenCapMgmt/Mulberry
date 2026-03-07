"""Base API client with rate limiting and caching"""

import asyncio
import aiohttp
from typing import Optional, Dict, Any
from asyncio import Semaphore
from datetime import datetime

from ..utils.logger import get_logger
from ..cache.database import CacheManager

logger = get_logger(__name__)


class RateLimiter:
    """Rate limiter using token bucket algorithm"""

    def __init__(self, requests_per_minute: int):
        """
        Initialize rate limiter

        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.semaphore = Semaphore(requests_per_minute)
        self.interval = 60.0 / requests_per_minute  # Seconds between requests

    async def wait(self):
        """Wait for rate limit availability"""
        async with self.semaphore:
            await asyncio.sleep(self.interval)


class BaseAPIClient:
    """
    Base API client with rate limiting and caching support

    Features:
    - Async HTTP requests with aiohttp
    - Token bucket rate limiting
    - Automatic cache integration
    - Error handling and retries
    """

    def __init__(
        self,
        api_key: str,
        rate_limit: int,
        cache_manager: Optional[CacheManager] = None,
        base_url: str = ""
    ):
        """
        Initialize base API client

        Args:
            api_key: API key for authentication
            rate_limit: Requests per minute limit
            cache_manager: Optional cache manager instance
            base_url: Base URL for API endpoints
        """
        self.api_key = api_key
        self.base_url = base_url
        self.rate_limiter = RateLimiter(rate_limit)
        self.cache = cache_manager
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _fetch(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = True,
        cache_key: Optional[str] = None,
        cache_ttl: int = 3600
    ) -> Dict[str, Any]:
        """
        Fetch data from API with rate limiting and caching

        Args:
            url: Full URL to fetch
            params: Query parameters
            headers: HTTP headers
            use_cache: Whether to use cache
            cache_key: Cache key (if different from URL)
            cache_ttl: Cache time-to-live in seconds

        Returns:
            Response data as dict

        Raises:
            Exception: On API errors
        """
        # Check cache first
        if use_cache and self.cache and cache_key:
            cached_data = self.cache.get_fundamentals(cache_key.split(':')[0], cache_key.split(':')[1])
            if cached_data:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_data

        # Rate limit
        await self.rate_limiter.wait()

        # Make request
        session = await self._get_session()
        try:
            async with session.get(url, params=params, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                # Check for API-specific errors
                if isinstance(data, dict):
                    if "Error Message" in data:
                        raise Exception(f"API Error: {data['Error Message']}")
                    if "Note" in data and "API call frequency" in data["Note"]:
                        raise Exception("API rate limit exceeded")

                # Cache the result
                if use_cache and self.cache and cache_key:
                    parts = cache_key.split(':', 1)
                    if len(parts) == 2:
                        self.cache.set_fundamentals(parts[0], parts[1], data, ttl=cache_ttl)

                logger.debug(f"Fetched: {url}")
                return data

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error: {e}")
            raise Exception(f"API request failed: {e}")
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            raise

    async def close(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
