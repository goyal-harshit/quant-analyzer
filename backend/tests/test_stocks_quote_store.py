"""
Integration test for the ingest-then-serve wiring in modules/stocks/service.py.

Verifies the stocks quote endpoint serves fresh rows from the market store, and
that a store miss falls back to the live path and writes through — using an
isolated SQLite store swapped in for AsyncSessionLocal.
"""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import pandas as pd

import models.market_store  # noqa: F401 — register market_* tables on Base
from models.database import Base
from services.market_store import read_bars, read_quote, upsert_bars, upsert_fundamentals, upsert_quote


@pytest.fixture
async def store(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite://", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    # The service imports AsyncSessionLocal from models.database at call time, so
    # patching the attribute redirects its store reads/writes to this test DB.
    import models.database as dbmod
    monkeypatch.setattr(dbmod, "AsyncSessionLocal", factory)
    yield factory
    await engine.dispose()


async def test_quote_served_from_store_when_fresh(store, monkeypatch):
    from modules.stocks import service

    async with store() as db:
        await upsert_quote(db, "RELIANCE", {
            "price": 2900, "name": "Reliance Industries", "source": "yahoo",
        })

    calls = {"live": 0}

    async def fake_live(t, refresh=False):
        calls["live"] += 1
        return {"price": 999}

    monkeypatch.setattr(service.data_service, "get_quote", fake_live)

    q = await service.get_quote("RELIANCE")
    assert q["price"] == 2900               # served from DB, not the live stub
    assert q["served_from"] == "db"
    assert q["name"] == "Reliance Industries"  # full payload preserved via raw
    assert calls["live"] == 0               # live source never touched


async def test_quote_miss_falls_back_and_writes_through(store, monkeypatch):
    from modules.stocks import service

    async def fake_live(t, refresh=False):
        return {"price": 1234, "name": "Infosys", "source": "yahoo"}

    monkeypatch.setattr(service.data_service, "get_quote", fake_live)

    q = await service.get_quote("INFY")
    assert q["price"] == 1234               # store empty -> live path

    async with store() as db:
        served = await read_quote(db, "INFY")
    assert served is not None               # write-through populated the store
    assert served["price"] == 1234
    assert served["served_from"] == "db"


async def test_refresh_bypasses_store_fast_path(store, monkeypatch):
    from modules.stocks import service

    async with store() as db:
        await upsert_quote(db, "RELIANCE", {"price": 2900, "source": "yahoo"})

    async def fake_live(t, refresh=False):
        return {"price": 555, "source": "yahoo"}

    monkeypatch.setattr(service.data_service, "get_quote", fake_live)

    q = await service.get_quote("RELIANCE", refresh=True)
    assert q["price"] == 555                # forced refresh -> live, not the stored 2900


# ── Fundamentals ──────────────────────────────────────────────────

async def test_fundamentals_served_from_store_when_fresh(store, monkeypatch):
    from modules.stocks import service

    async with store() as db:
        await upsert_fundamentals(db, "HDFCBANK", {
            "pe_ratio": 18.5, "roe": 16.2, "source": "screener.in",
        })

    calls = {"fund": 0}

    async def fake_fund(t, refresh=False):
        calls["fund"] += 1
        return {"pe_ratio": 99}

    async def empty_hist(t, period="1y", interval="1d", refresh=False):
        return pd.DataFrame()  # skip factor block, no history write

    monkeypatch.setattr(service.data_service, "get_fundamentals", fake_fund)
    monkeypatch.setattr(service.data_service, "get_price_history", empty_hist)

    data = await service.get_fundamentals("HDFCBANK")
    assert data["pe_ratio"] == 18.5         # served from store, not the live stub
    assert data["served_from"] == "db"
    assert calls["fund"] == 0               # live fundamentals never fetched


# ── History (coverage-gated) ──────────────────────────────────────

def _daily_df(n: int) -> pd.DataFrame:
    idx = pd.date_range(end=pd.Timestamp.utcnow().normalize(), periods=n)
    return pd.DataFrame({
        "open": [10.0] * n, "high": [11.0] * n, "low": [9.0] * n,
        "close": [10.5] * n, "volume": [1000] * n,
    }, index=idx)


async def test_history_served_from_store_with_sufficient_coverage(store, monkeypatch):
    from modules.stocks import service

    async with store() as db:
        await upsert_bars(db, "RELIANCE", _daily_df(230), source="yahoo")  # > 0.6*365

    calls = {"hist": 0}

    async def fake_hist(t, period, interval="1d", refresh=False):
        calls["hist"] += 1
        return pd.DataFrame()

    monkeypatch.setattr(service.data_service, "get_price_history", fake_hist)

    out = await service.get_history("RELIANCE", period="1y")
    assert len(out["data"]) == 230          # served straight from the store
    assert calls["hist"] == 0               # live history never fetched


async def test_history_falls_through_when_coverage_insufficient(store, monkeypatch):
    from modules.stocks import service

    async with store() as db:
        await upsert_bars(db, "RELIANCE", _daily_df(10), source="yahoo")  # < threshold

    async def fake_hist(t, period, interval="1d", refresh=False):
        return _daily_df(60)                # live returns a fuller series

    monkeypatch.setattr(service.data_service, "get_price_history", fake_hist)

    out = await service.get_history("RELIANCE", period="1y")
    assert len(out["data"]) == 60           # fell through to live (no under-serving)

    # write-through should have refreshed the store to the fuller series
    async with store() as db:
        stored = await read_bars(db, "RELIANCE", "1y")
    assert len(stored) == 60
