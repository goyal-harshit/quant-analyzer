"""
cache_service.py — Redis-backed caching with in-memory fallback.
Cache-aside pattern: get_or_compute checks cache first, calls compute_func on miss.
Gracefully degrades when Redis is unavailable.
"""
import asyncio
import json
import logging
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Default TTLs (seconds)
TTL_QUOTE = 15
TTL_FUNDAMENTALS = 3600
TTL_PRICE_HISTORY = 300
TTL_FACTOR_SCORES = 600
TTL_MACRO = 86400
TTL_NEWS = 600

_redis_instance = None


def _record_cache(hit: bool) -> None:
    """Record a cache hit/miss for the /metrics cache-hit-rate gauge (best-effort)."""
    try:
        from services.observability import metrics
        metrics.inc("cache_requests_total", {"result": "hit" if hit else "miss"})
    except Exception:
        pass


class CacheService:
    # After a failed connect, don't retry on every call — a down Redis would
    # otherwise turn a batch of N cache gets into N connection timeouts
    # (e.g. a 500-name screen stalling for minutes). Retry at most once per window.
    _RECONNECT_COOLDOWN = 30.0

    def __init__(self, redis_url: str = None):
        import os
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis = None
        self._in_memory = {}
        self._connect_retry_at = 0.0

    async def _connect(self):
        global _redis_instance
        if _redis_instance is not None:
            self._redis = _redis_instance
            return
        # Back off from hammering an unreachable Redis on every get/set.
        if time.monotonic() < self._connect_retry_at:
            return
        if not self.redis_url:
            self._redis = None
            self._connect_retry_at = time.monotonic() + self._RECONNECT_COOLDOWN
            return
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self.redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
            )
            await self._redis.ping()
            logger.info("Redis cache connected")
            _redis_instance = self._redis
        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory cache: {e}")
            self._redis = None
            self._connect_retry_at = time.monotonic() + self._RECONNECT_COOLDOWN

    def _trip(self, e: Exception) -> None:
        """A live Redis op just failed (e.g. the server died mid-session). Drop the
        handle and start the cooldown so the rest of a batch falls straight to the
        in-memory store instead of paying socket_timeout on every call — otherwise a
        500-name screen becomes 500 × timeout. Clearing the shared global makes all
        CacheService references back off together."""
        global _redis_instance
        logger.warning(f"Redis op failed, backing off to in-memory cache: {e}")
        self._redis = None
        _redis_instance = None
        self._connect_retry_at = time.monotonic() + self._RECONNECT_COOLDOWN

    async def get(self, key: str) -> Optional[str]:
        value = await self._get_raw(key)
        _record_cache(value is not None)
        return value

    async def _get_raw(self, key: str) -> Optional[str]:
        if self._redis is None:
            await self._connect()
        if self._redis:
            try:
                return await self._redis.get(key)
            except Exception as e:
                self._trip(e)
        # In-memory fallback with TTL enforcement (value, expires_at).
        entry = self._in_memory.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at is not None and time.monotonic() > expires_at:
            self._in_memory.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: str, ttl: int = 300):
        if self._redis is None:
            await self._connect()
        if self._redis:
            try:
                await self._redis.setex(key, ttl, value)
                return
            except Exception as e:
                self._trip(e)
        # Bound the in-memory fallback so it can't grow unbounded.
        if len(self._in_memory) > 5000:
            self._in_memory.clear()
        self._in_memory[key] = (value, (time.monotonic() + ttl) if ttl else None)

    async def get_or_compute(self, key: str, ttl: int, compute_func: Callable[[], Any]) -> str:
        cached = await self.get(key)
        if cached is not None:
            return cached
        # Correctly detect coroutine functions (the old hasattr(__await__) check
        # was always False for an async def and silently never awaited).
        result = compute_func()
        if asyncio.iscoroutine(result):
            result = await result
        if isinstance(result, (dict, list)):
            result_str = json.dumps(result)
        else:
            result_str = str(result)
        await self.set(key, result_str, ttl)
        return result_str

    async def invalidate(self, pattern: str):
        if self._redis is None:
            await self._connect()
        if self._redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor=cursor, match=pattern, count=100)
                    if keys:
                        await self._redis.delete(*keys)
                    if cursor == 0:
                        break
            except Exception as e:
                self._trip(e)
        self._in_memory = {k: v for k, v in self._in_memory.items() if pattern not in k}

    async def health(self) -> bool:
        if self._redis is None:
            await self._connect()
        if self._redis:
            try:
                return await self._redis.ping()
            except Exception:
                return False
        return bool(self._in_memory)


cache = CacheService()


def get_cache() -> CacheService:
    return cache
