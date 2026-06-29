"""
Tests for the resilience primitives (services/reliability.py).

These use injected clocks / sleeps so behaviour is deterministic and the suite
never actually waits in real time.
"""


import pytest

from services.reliability import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    SourceGuard,
    TokenBucket,
    retry_async,
)


class FakeClock:
    """Manually-advanced monotonic clock."""

    def __init__(self, t: float = 1000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


# ── CircuitBreaker ────────────────────────────────────────────────

async def test_breaker_opens_after_threshold():
    clock = FakeClock()
    cb = CircuitBreaker("t", failure_threshold=3, recovery_timeout=30, clock=clock)

    assert cb.state == CircuitState.CLOSED
    for _ in range(2):
        await cb.record_failure()
    assert cb.state == CircuitState.CLOSED  # not yet at threshold
    await cb.record_failure()
    assert cb.state == CircuitState.OPEN
    # While open, calls are short-circuited.
    assert await cb.allow() is False


async def test_breaker_half_open_then_close_on_success():
    clock = FakeClock()
    cb = CircuitBreaker("t", failure_threshold=1, recovery_timeout=30, clock=clock)
    await cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert await cb.allow() is False

    clock.advance(31)  # cooldown elapsed
    assert await cb.allow() is True          # transitions to HALF_OPEN, takes probe slot
    assert cb.state == CircuitState.HALF_OPEN
    assert await cb.allow() is False         # only one probe at a time
    await cb.record_success()
    assert cb.state == CircuitState.CLOSED


async def test_breaker_half_open_failure_reopens():
    clock = FakeClock()
    cb = CircuitBreaker("t", failure_threshold=1, recovery_timeout=10, clock=clock)
    await cb.record_failure()
    clock.advance(11)
    assert await cb.allow() is True          # HALF_OPEN probe
    await cb.record_failure()                # probe fails
    assert cb.state == CircuitState.OPEN
    assert await cb.allow() is False         # cooldown restarts


async def test_breaker_success_resets_failure_count():
    cb = CircuitBreaker("t", failure_threshold=3)
    await cb.record_failure()
    await cb.record_failure()
    await cb.record_success()
    assert cb.consecutive_failures == 0
    await cb.record_failure()
    assert cb.state == CircuitState.CLOSED   # count restarted, not at threshold


async def test_breaker_call_short_circuits_when_open():
    clock = FakeClock()
    cb = CircuitBreaker("t", failure_threshold=1, recovery_timeout=30, clock=clock)

    async def boom():
        raise ValueError("source down")

    with pytest.raises(ValueError):
        await cb.call(boom)
    assert cb.state == CircuitState.OPEN

    calls = 0

    async def ok():
        nonlocal calls
        calls += 1
        return "ok"

    with pytest.raises(CircuitOpenError):
        await cb.call(ok)
    assert calls == 0  # never invoked — short-circuited


# ── TokenBucket ───────────────────────────────────────────────────

async def test_token_bucket_allows_burst_up_to_capacity():
    clock = FakeClock()
    slept = []

    async def fake_sleep(d):
        slept.append(d)

    tb = TokenBucket(rate=1.0, capacity=3.0, clock=clock, sleep=fake_sleep)
    for _ in range(3):
        await tb.acquire()
    assert slept == []  # burst within capacity, no waiting


async def test_token_bucket_throttles_beyond_capacity():
    clock = FakeClock()
    slept = []

    async def fake_sleep(d):
        slept.append(d)
        clock.advance(d)  # simulate time passing during the wait

    tb = TokenBucket(rate=2.0, capacity=2.0, clock=clock, sleep=fake_sleep)
    for _ in range(2):
        await tb.acquire()       # drains the bucket, no sleep
    await tb.acquire()           # must wait for one token at 2/sec -> 0.5s
    assert len(slept) == 1
    assert abs(slept[0] - 0.5) < 1e-9


async def test_token_bucket_refills_over_time():
    clock = FakeClock()

    async def fake_sleep(d):
        clock.advance(d)

    tb = TokenBucket(rate=4.0, capacity=4.0, clock=clock, sleep=fake_sleep)
    for _ in range(4):
        await tb.acquire()
    clock.advance(1.0)           # 1s -> +4 tokens (capped at 4)
    for _ in range(4):
        await tb.acquire()       # all served from refill, no sleep needed


def test_token_bucket_rejects_bad_rate():
    with pytest.raises(ValueError):
        TokenBucket(rate=0)


# ── retry_async ───────────────────────────────────────────────────

async def test_retry_succeeds_after_transient_failures():
    attempts = 0

    async def flaky():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("transient")
        return "ok"

    out = await retry_async(flaky, retries=3, base_delay=0.1, sleep=_noop_sleep, rng=lambda: 0.0)
    assert out == "ok"
    assert attempts == 3


async def test_retry_exhausts_and_raises():
    attempts = 0

    async def always_fail():
        nonlocal attempts
        attempts += 1
        raise TimeoutError("nope")

    with pytest.raises(TimeoutError):
        await retry_async(always_fail, retries=2, base_delay=0.1, sleep=_noop_sleep, rng=lambda: 0.0)
    assert attempts == 3  # initial + 2 retries


async def test_retry_gives_up_immediately_on_open_circuit():
    attempts = 0

    async def short_circuited():
        nonlocal attempts
        attempts += 1
        raise CircuitOpenError("yahoo", 10.0)

    with pytest.raises(CircuitOpenError):
        await retry_async(short_circuited, retries=5, sleep=_noop_sleep)
    assert attempts == 1  # never retried — give_up_on


async def test_retry_backoff_grows_exponentially():
    delays = []

    async def record_sleep(d):
        delays.append(d)

    async def always_fail():
        raise ValueError("x")

    with pytest.raises(ValueError):
        await retry_async(
            always_fail, retries=3, base_delay=1.0, jitter=0.0,
            sleep=record_sleep, rng=lambda: 0.0,
        )
    assert delays == [1.0, 2.0, 4.0]  # 2**0, 2**1, 2**2


# ── SourceGuard integration ───────────────────────────────────────

async def test_source_guard_combines_breaker_and_retry():
    cb = CircuitBreaker("g", failure_threshold=10)
    guard = SourceGuard("g", cb, bucket=None, retries=2, base_delay=0.0)
    attempts = 0

    async def flaky():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ConnectionError("blip")
        return 42

    # base_delay=0 so retry sleeps are zero-length real awaits.
    out = await guard(flaky)
    assert out == 42
    assert attempts == 2


async def _noop_sleep(_d):
    return None
