"""
reliability.py — resilience primitives for fragile free data sources.

The platform depends on free, unofficial endpoints (Yahoo v8, cookie-warmed NSE,
screener.in scraping, mfapi.in) that block under load and have no SLA. CONTEXT.md
documents past 429/403 "storms" where repeated failures stampede a struggling
source and saturate the single worker.

This module provides three stdlib-only, async-friendly primitives — wired in at
each external HTTP call site so a flaky source degrades gracefully instead of
cascading:

  * CircuitBreaker  — trips OPEN after N consecutive failures, short-circuits
                      calls for a cooldown, then probes via HALF_OPEN.
  * TokenBucket     — per-source rate limiter (steady requests/sec, small burst).
  * retry_async     — bounded retry with exponential backoff + jitter.
  * guard()         — convenience: rate-limit + breaker + retry around one coro.

Everything is dependency-free and time-injectable so it is deterministically
unit-testable without sleeping in real time.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# HTTP status codes that mean "the source is unhealthy / throttling us" and
# should count against a circuit breaker. A 404/400 means the resource simply
# has no data (a *healthy* response) and must NOT trip the breaker — otherwise a
# batch of unknown symbols would needlessly open the circuit.
SOURCE_DOWN_STATUS = frozenset({403, 408, 425, 429, 500, 502, 503, 504})

# A monotonic clock, injectable for tests.
Clock = Callable[[], float]


class CircuitOpenError(RuntimeError):
    """Raised when a call is short-circuited because the breaker is OPEN."""

    def __init__(self, name: str, retry_after: float):
        self.name = name
        self.retry_after = retry_after
        super().__init__(f"circuit '{name}' is open; retry in {retry_after:.1f}s")


class CircuitState(str, Enum):
    CLOSED = "closed"      # healthy — calls flow through
    OPEN = "open"          # tripped — calls short-circuit immediately
    HALF_OPEN = "half_open"  # probing — a limited number of trial calls allowed


class CircuitBreaker:
    """Per-source circuit breaker.

    Opens after ``failure_threshold`` consecutive failures, stays OPEN for
    ``recovery_timeout`` seconds, then allows a single trial call (HALF_OPEN).
    A successful trial closes the breaker; a failed trial re-opens it.
    """

    def __init__(
        self,
        name: str,
        *,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        clock: Optional[Clock] = None,
    ):
        self.name = name
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_timeout = recovery_timeout
        self._clock = clock or time.monotonic
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._opened_at = 0.0
        self._half_open_inflight = False
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def _retry_after(self) -> float:
        return max(0.0, self.recovery_timeout - (self._clock() - self._opened_at))

    async def allow(self) -> bool:
        """Return True if a call may proceed now, transitioning state as needed.

        When it returns True in HALF_OPEN, the caller holds the single probe slot
        and MUST report the outcome via record_success/record_failure.
        """
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.OPEN:
                if self._retry_after() <= 0:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_inflight = True
                    return True
                return False
            # HALF_OPEN — admit exactly one probe at a time.
            if not self._half_open_inflight:
                self._half_open_inflight = True
                return True
            return False

    async def record_success(self) -> None:
        async with self._lock:
            self._consecutive_failures = 0
            self._half_open_inflight = False
            if self._state != CircuitState.CLOSED:
                logger.info("circuit '%s' closed after success", self.name)
            self._state = CircuitState.CLOSED

    async def record_failure(self) -> None:
        async with self._lock:
            self._consecutive_failures += 1
            self._half_open_inflight = False
            if self._state == CircuitState.HALF_OPEN:
                self._trip()
            elif self._consecutive_failures >= self.failure_threshold:
                self._trip()

    def _trip(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()
        logger.warning(
            "circuit '%s' OPEN (%d consecutive failures); cooling down %.0fs",
            self.name, self._consecutive_failures, self.recovery_timeout,
        )

    async def call(self, func: Callable[[], Awaitable[T]]) -> T:
        """Run ``func`` under the breaker. Raises CircuitOpenError if short-circuited."""
        if not await self.allow():
            raise CircuitOpenError(self.name, self._retry_after())
        try:
            result = await func()
        except Exception:
            await self.record_failure()
            raise
        else:
            await self.record_success()
            return result


class TokenBucket:
    """Async token-bucket rate limiter.

    Refills at ``rate`` tokens/sec up to ``capacity``. ``acquire`` waits until a
    token is available, smoothing bursts into a steady request rate (this is what
    keeps screener.in / NSE from seeing the burst patterns that get blocked).
    """

    def __init__(
        self,
        rate: float,
        capacity: Optional[float] = None,
        *,
        clock: Optional[Clock] = None,
        sleep: Optional[Callable[[float], Awaitable[None]]] = None,
    ):
        if rate <= 0:
            raise ValueError("rate must be > 0")
        self.rate = rate
        self.capacity = capacity if capacity is not None else max(1.0, rate)
        self._clock = clock or time.monotonic
        self._sleep = sleep or asyncio.sleep
        self._tokens = self.capacity
        self._updated = self._clock()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._updated
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            self._updated = now

    async def acquire(self, tokens: float = 1.0) -> None:
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                deficit = tokens - self._tokens
                wait = deficit / self.rate
            await self._sleep(wait)


async def retry_async(
    func: Callable[[], Awaitable[T]],
    *,
    retries: int = 2,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    jitter: float = 0.25,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    give_up_on: tuple[type[BaseException], ...] = (CircuitOpenError,),
    sleep: Optional[Callable[[float], Awaitable[None]]] = None,
    rng: Optional[Callable[[], float]] = None,
) -> T:
    """Call ``func`` up to ``retries`` extra times with exponential backoff + jitter.

    ``give_up_on`` exceptions (default: an open circuit) are re-raised immediately —
    retrying a tripped breaker is pointless and only burns the worker.
    """
    _sleep = sleep or asyncio.sleep
    _rng = rng or random.random
    attempt = 0
    while True:
        try:
            return await func()
        except give_up_on:
            raise
        except retry_on as exc:
            if attempt >= retries:
                raise
            delay = min(max_delay, base_delay * (2 ** attempt))
            delay += delay * jitter * _rng()
            logger.info(
                "retry %d/%d after %s: %s", attempt + 1, retries, type(exc).__name__, exc
            )
            await _sleep(delay)
            attempt += 1


@dataclass
class SourceGuard:
    """Bundles a breaker + rate limiter + retry policy for one named source."""

    name: str
    breaker: CircuitBreaker
    bucket: Optional[TokenBucket] = None
    retries: int = 2
    base_delay: float = 0.5

    async def __call__(self, func: Callable[[], Awaitable[T]]) -> T:
        async def _attempt() -> T:
            if self.bucket is not None:
                await self.bucket.acquire()
            return await self.breaker.call(func)

        return await retry_async(_attempt, retries=self.retries, base_delay=self.base_delay)


# ── Registry ──────────────────────────────────────────────────────
# Named, process-wide guards so every call site to a given source shares one
# breaker + rate limiter (a per-call breaker would never trip).
_guards: dict[str, SourceGuard] = {}
_registry_lock = asyncio.Lock()


# Per-source tuning. Rates are deliberately conservative for the scrape/cookie
# sources that block on bursts; Yahoo's JSON API tolerates more.
_DEFAULTS: dict[str, dict] = {
    "yahoo":     {"rate": 8.0,  "capacity": 12.0, "failure_threshold": 6, "recovery_timeout": 30.0, "retries": 2},
    "screener":  {"rate": 0.66, "capacity": 2.0,  "failure_threshold": 4, "recovery_timeout": 60.0, "retries": 1},
    "nse":       {"rate": 2.0,  "capacity": 3.0,  "failure_threshold": 4, "recovery_timeout": 45.0, "retries": 1},
    "mfapi":     {"rate": 5.0,  "capacity": 8.0,  "failure_threshold": 5, "recovery_timeout": 30.0, "retries": 2},
    "worldbank": {"rate": 4.0,  "capacity": 6.0,  "failure_threshold": 5, "recovery_timeout": 30.0, "retries": 2},
    # NSE-direct libraries (nsepython / jugaad-data) block from many hosts, so
    # they trip fast (3 failures) and stay open a long time (no retries, 2-min
    # cooldown) — cheap to keep in the fallback chain even where they don't work.
    "nsepython": {"rate": 1.5, "capacity": 2.0,  "failure_threshold": 3, "recovery_timeout": 120.0, "retries": 0},
    "jugaad":    {"rate": 1.5, "capacity": 2.0,  "failure_threshold": 3, "recovery_timeout": 120.0, "retries": 0},
}
_GENERIC = {"rate": 5.0, "capacity": 8.0, "failure_threshold": 5, "recovery_timeout": 30.0, "retries": 2}


def _build_guard(name: str) -> SourceGuard:
    cfg = _DEFAULTS.get(name, _GENERIC)
    breaker = CircuitBreaker(
        name,
        failure_threshold=cfg["failure_threshold"],
        recovery_timeout=cfg["recovery_timeout"],
    )
    bucket = TokenBucket(cfg["rate"], cfg["capacity"])
    return SourceGuard(name, breaker, bucket, retries=cfg["retries"])


async def get_guard(name: str) -> SourceGuard:
    """Return the process-wide guard for ``name``, creating it on first use."""
    guard = _guards.get(name)
    if guard is not None:
        return guard
    async with _registry_lock:
        guard = _guards.get(name)
        if guard is None:
            guard = _build_guard(name)
            _guards[name] = guard
    return guard


async def guard_call(name: str, func: Callable[[], Awaitable[T]]) -> T:
    """Run ``func`` under the named source's guard (rate-limit + breaker + retry)."""
    guard = await get_guard(name)
    return await guard(func)


def breaker_states() -> dict[str, dict]:
    """Snapshot of every known source's breaker — for the /health observability hook."""
    return {
        name: {
            "state": g.breaker.state.value,
            "consecutive_failures": g.breaker.consecutive_failures,
        }
        for name, g in _guards.items()
    }
