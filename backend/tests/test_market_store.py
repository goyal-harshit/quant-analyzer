"""
Tests for the ingest-then-serve store (services/market_store.py + DBProvider).

Runs against an isolated in-memory-ish SQLite DB created per test, so the
upsert / freshness-read / provider round-trips are verified without Postgres.
"""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import services.market_store as ms
from models.database import Base
from models.market_store import MarketBar, MarketFundamental, MarketQuote  # noqa: F401
from services.providers import DBProvider


@pytest.fixture
async def session_factory():
    # A dedicated file-less SQLite engine per test (shared-cache in-memory so the
    # async connection pool sees the same DB across sessions).
    engine = create_async_engine("sqlite+aiosqlite://", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


# ── upsert + read round-trips ─────────────────────────────────────

async def test_quote_upsert_and_read(session_factory):
    async with session_factory() as db:
        await ms.upsert_quote(db, "RELIANCE", {
            "price": 2850.5, "prev_close": 2838.2, "change": 12.3, "change_pct": 0.43,
            "volume": 1_000_000, "source": "yahoo",
        })
    async with session_factory() as db:
        q = await ms.read_quote(db, "RELIANCE")
    assert q["price"] == 2850.5
    assert q["source"] == "yahoo"        # original provenance preserved
    assert q["served_from"] == "db"
    assert q["age_seconds"] >= 0


async def test_quote_upsert_is_idempotent_overwrite(session_factory):
    async with session_factory() as db:
        await ms.upsert_quote(db, "TCS", {"price": 100, "source": "yahoo"})
        await ms.upsert_quote(db, "TCS", {"price": 200, "source": "nsepython"})
    async with session_factory() as db:
        q = await ms.read_quote(db, "TCS")
    assert q["price"] == 200            # latest write wins (one row per ticker)
    assert q["source"] == "nsepython"


async def test_quote_freshness_gate(session_factory):
    async with session_factory() as db:
        await ms.upsert_quote(db, "INFY", {"price": 1500, "source": "yahoo"})
        # Backdate fetched_at well beyond the max_age window.
        row = await db.get(MarketQuote, "INFY")
        row.fetched_at = datetime.now(timezone.utc) - timedelta(seconds=600)
        await db.commit()
    async with session_factory() as db:
        assert await ms.read_quote(db, "INFY", max_age=120) is None     # stale -> miss
        assert await ms.read_quote(db, "INFY", max_age=None) is not None  # gate disabled


async def test_fundamentals_upsert_and_read(session_factory):
    async with session_factory() as db:
        await ms.upsert_fundamentals(db, "HDFCBANK", {
            "pe_ratio": 18.5, "roe": 16.2, "debt_equity": 0.8, "source": "screener.in",
        })
    async with session_factory() as db:
        f = await ms.read_fundamentals(db, "HDFCBANK")
    assert f["pe_ratio"] == 18.5
    assert f["roe"] == 16.2
    assert f["served_from"] == "db"


async def test_bars_upsert_replaces_and_reads_dataframe(session_factory):
    idx = pd.date_range("2026-01-01", periods=5)
    df = pd.DataFrame({
        "open": [1, 2, 3, 4, 5], "high": [2, 3, 4, 5, 6], "low": [0, 1, 2, 3, 4],
        "close": [1.5, 2.5, 3.5, 4.5, 5.5], "volume": [10, 20, 30, 40, 50],
    }, index=idx)
    async with session_factory() as db:
        n = await ms.upsert_bars(db, "WIPRO", df, source="yahoo")
        assert n == 5
        # Re-ingest with fewer bars -> full replace, not append.
        n2 = await ms.upsert_bars(db, "WIPRO", df.head(3), source="yahoo")
        assert n2 == 3
    async with session_factory() as db:
        out = await ms.read_bars(db, "WIPRO", "1y")
    assert len(out) == 3                       # replaced, not 5+3
    assert list(out.columns) == ["open", "high", "low", "close", "volume"]


async def test_read_bars_period_window(session_factory):
    old = pd.date_range("2020-01-01", periods=3)        # far outside a 1mo window
    recent = pd.date_range(datetime.now(timezone.utc).date() - timedelta(days=5), periods=3)
    df = pd.DataFrame({
        "open": [1, 1, 1, 2, 2, 2], "high": [1, 1, 1, 2, 2, 2],
        "low": [1, 1, 1, 2, 2, 2], "close": [1, 1, 1, 2, 2, 2], "volume": [1] * 6,
    }, index=old.append(recent))
    async with session_factory() as db:
        await ms.upsert_bars(db, "SBIN", df, source="yahoo")
    async with session_factory() as db:
        out = await ms.read_bars(db, "SBIN", "1mo")
    assert len(out) == 3                       # only the recent bars fall in-window


async def test_read_quote_missing_returns_none(session_factory):
    async with session_factory() as db:
        assert await ms.read_quote(db, "NOPE") is None


# ── DBProvider over the store ─────────────────────────────────────

async def test_db_provider_reads_from_store(session_factory):
    async with session_factory() as db:
        await ms.upsert_quote(db, "RELIANCE", {"price": 2900, "source": "yahoo"})

    prov = DBProvider(session_factory=session_factory, quote_max_age=None)
    q = await prov.get_quote("RELIANCE")
    assert q["price"] == 2900
    assert q["served_from"] == "db"


async def test_db_provider_miss_returns_none_not_raises(session_factory):
    prov = DBProvider(session_factory=session_factory)
    assert await prov.get_quote("MISSING") is None


async def test_db_provider_swallows_db_errors():
    # A broken session factory must not propagate — provider degrades to None so
    # the chain falls through to a live source.
    def boom():
        raise RuntimeError("db down")

    prov = DBProvider(session_factory=boom)
    assert await prov.get_quote("X") is None
    assert await prov.get_fundamentals("X") is None
    assert await prov.get_history("X") is None
