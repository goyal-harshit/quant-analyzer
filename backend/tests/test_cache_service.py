"""
Tests for services/cache_service.py graceful Redis degradation.

Regression guard for the batch-stall bug: when a live Redis dies mid-session,
each subsequent op must NOT pay the socket timeout. A single failure has to trip
the reconnect cooldown so the rest of a 500-name screen falls straight to the
in-memory store instead of 500 × timeout.
"""
import time

import services.cache_service as cs
from services.cache_service import CacheService


class FakeDeadRedis:
    """A Redis handle that connected fine but is now unreachable — every op raises."""

    def __init__(self):
        self.get_calls = 0
        self.setex_calls = 0

    async def get(self, key):
        self.get_calls += 1
        raise ConnectionError("redis died mid-session")

    async def setex(self, key, ttl, value):
        self.setex_calls += 1
        raise ConnectionError("redis died mid-session")


async def test_failed_get_trips_cooldown_and_falls_back(monkeypatch):
    monkeypatch.setattr(cs, "_redis_instance", None, raising=False)
    c = CacheService(redis_url="redis://localhost:6379/0")
    # Seed a value in the in-memory fallback directly.
    c._in_memory["k"] = ("v", None)

    fake = FakeDeadRedis()
    c._redis = fake

    # A get against the dead handle fails once, then falls back to in-memory.
    assert await c.get("k") == "v"
    assert fake.get_calls == 1

    # The failure must have tripped the cooldown and dropped the handle+global.
    assert c._redis is None
    assert cs._redis_instance is None
    assert c._connect_retry_at > time.monotonic()


async def test_cooldown_prevents_further_redis_calls(monkeypatch):
    monkeypatch.setattr(cs, "_redis_instance", None, raising=False)
    c = CacheService(redis_url="redis://localhost:6379/0")
    c._in_memory["k"] = ("v", None)
    fake = FakeDeadRedis()
    c._redis = fake

    # First call trips the cooldown.
    await c.get("k")
    assert fake.get_calls == 1

    # 50 more gets while the cooldown window is open must never touch Redis again.
    for _ in range(50):
        assert await c.get("k") == "v"
    assert fake.get_calls == 1  # still just the one failed call


async def test_failed_set_also_trips_and_still_stores(monkeypatch):
    monkeypatch.setattr(cs, "_redis_instance", None, raising=False)
    c = CacheService(redis_url="redis://localhost:6379/0")
    fake = FakeDeadRedis()
    c._redis = fake

    # A set against the dead handle trips the cooldown but still persists in-memory.
    await c.set("k", "v", ttl=60)
    assert fake.setex_calls == 1
    assert c._redis is None
    assert c._connect_retry_at > time.monotonic()
    assert await c.get("k") == "v"
    # The get above must not have re-hit Redis (cooldown still active).
    assert fake.get_calls == 0
