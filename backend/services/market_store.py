"""
market_store.py — read/write + ingestion for the ingest-then-serve store.

Write side (`ingest_*`): fetch from the **live-only** provider chain (Yahoo / NSE
libs / seed — never the DB, to avoid a read-your-own-write loop) and upsert into the
`market_*` tables, stamping `source` + `fetched_at`.

Read side (`read_*`): return stored rows with a freshness gate — if a row is older
than `max_age`, it's treated as a miss so the chain falls through to a live fetch.
This is the core of "endpoints read from DB; freshness is a column, not a fetch".
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.market_store import MarketBar, MarketFundamental, MarketQuote

logger = logging.getLogger(__name__)

# Default freshness windows (seconds): how old a stored row may be before a read
# treats it as a miss. Quotes go stale fast; fundamentals change slowly.
QUOTE_MAX_AGE = 120
FUNDAMENTALS_MAX_AGE = 86_400  # 24h

_PERIOD_DAYS = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}

_QUOTE_FIELDS = (
    "price", "prev_close", "change", "change_pct", "open",
    "day_high", "day_low", "volume", "market_cap",
)
_FUNDAMENTAL_FIELDS = (
    "pe_ratio", "pb_ratio", "ev_ebitda", "ps_ratio", "roe", "roa",
    "gross_margin", "ebitda_margin", "net_margin", "revenue_growth",
    "earnings_growth", "debt_equity", "dividend_yield", "market_cap",
)


def _age_seconds(dt: Optional[datetime]) -> float:
    if dt is None:
        return float("inf")
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:  # SQLite stores naive UTC; align before subtracting
        now = now.replace(tzinfo=None)
    return (now - dt).total_seconds()


def _num(v) -> Optional[float]:
    try:
        if v is None:
            return None
        f = float(v)
        return f if f == f else None  # drop NaN
    except (TypeError, ValueError):
        return None


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


# ── WRITE ─────────────────────────────────────────────────────────
async def upsert_quote(db: AsyncSession, ticker: str, quote: dict) -> None:
    ticker = ticker.upper()
    row = MarketQuote(
        ticker=ticker,
        source=quote.get("source") or "unknown",
        as_of=_parse_dt(quote.get("as_of")),
        fetched_at=datetime.now(timezone.utc),
        raw=dict(quote),
        **{f: _num(quote.get(f)) for f in _QUOTE_FIELDS},
    )
    await db.merge(row)
    await db.commit()


async def upsert_fundamentals(db: AsyncSession, ticker: str, fund: dict) -> None:
    ticker = ticker.upper()
    row = MarketFundamental(
        ticker=ticker,
        source=fund.get("source") or "unknown",
        as_of=_parse_dt(fund.get("as_of")),
        fetched_at=datetime.now(timezone.utc),
        **{f: _num(fund.get(f)) for f in _FUNDAMENTAL_FIELDS},
    )
    await db.merge(row)
    await db.commit()


async def upsert_bars(db: AsyncSession, ticker: str, df: pd.DataFrame, source: str) -> int:
    """Idempotent full refresh: replace this ticker's bars with the given frame."""
    ticker = ticker.upper()
    if df is None or df.empty:
        return 0
    await db.execute(delete(MarketBar).where(MarketBar.ticker == ticker))
    now = datetime.now(timezone.utc)
    count = 0
    for idx, r in df.iterrows():
        dt = pd.Timestamp(idx).to_pydatetime()
        db.add(MarketBar(
            ticker=ticker, date=dt,
            open=_num(r.get("open")), high=_num(r.get("high")),
            low=_num(r.get("low")), close=_num(r.get("close")),
            volume=_num(r.get("volume")), source=source, fetched_at=now,
        ))
        count += 1
    await db.commit()
    return count


# ── READ (freshness-gated) ────────────────────────────────────────
async def read_quote(db: AsyncSession, ticker: str, max_age: Optional[float] = QUOTE_MAX_AGE) -> Optional[dict]:
    row = await db.get(MarketQuote, ticker.upper())
    if row is None or row.price is None:
        return None
    age = _age_seconds(row.fetched_at)
    if max_age is not None and age > max_age:
        return None
    # Prefer the full original payload (preserves name/52w/currency/…); fall back
    # to the typed columns if no raw snapshot was stored.
    out = dict(row.raw) if row.raw else {f: getattr(row, f) for f in _QUOTE_FIELDS}
    out.update(
        ticker=row.ticker, source=row.source,
        as_of=_iso(row.as_of) or out.get("as_of"),
        fetched_at=_iso(row.fetched_at), age_seconds=round(age, 1), served_from="db",
    )
    return out


async def read_fundamentals(db: AsyncSession, ticker: str, max_age: Optional[float] = FUNDAMENTALS_MAX_AGE) -> Optional[dict]:
    row = await db.get(MarketFundamental, ticker.upper())
    if row is None:
        return None
    if row.pe_ratio is None and row.roe is None:
        return None
    age = _age_seconds(row.fetched_at)
    if max_age is not None and age > max_age:
        return None
    out = {f: getattr(row, f) for f in _FUNDAMENTAL_FIELDS}
    out.update(
        ticker=row.ticker, source=row.source, as_of=_iso(row.as_of),
        fetched_at=_iso(row.fetched_at), age_seconds=round(age, 1), served_from="db",
    )
    return out


async def read_bars(db: AsyncSession, ticker: str, period: str = "1y") -> pd.DataFrame:
    days = _PERIOD_DAYS.get(period, 365)
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    stmt = (
        select(MarketBar)
        .where(MarketBar.ticker == ticker.upper())
        .order_by(MarketBar.date)
    )
    rows = (await db.execute(stmt)).scalars().all()
    rows = [r for r in rows if _to_naive(r.date) >= cutoff]
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(
        {"open": [r.open for r in rows], "high": [r.high for r in rows],
         "low": [r.low for r in rows], "close": [r.close for r in rows],
         "volume": [r.volume for r in rows]},
        index=pd.to_datetime([r.date for r in rows]),
    )
    return df


# ── INGESTION (live -> DB) ────────────────────────────────────────
async def ingest_quote(db: AsyncSession, ticker: str) -> bool:
    from services.providers import live_data
    q = await live_data.get_quote(ticker)
    if q and q.get("price"):
        await upsert_quote(db, ticker, q)
        return True
    return False


async def ingest_fundamentals(db: AsyncSession, ticker: str) -> bool:
    from services.providers import live_data
    f = await live_data.get_fundamentals(ticker)
    if f and (f.get("pe_ratio") is not None or f.get("roe") is not None):
        await upsert_fundamentals(db, ticker, f)
        return True
    return False


async def ingest_history(db: AsyncSession, ticker: str, period: str = "2y") -> int:
    from services.providers import live_data
    df = await live_data.get_history(ticker, period)
    if df is None or df.empty:
        return 0
    source = "live"
    return await upsert_bars(db, ticker, df, source)


# ── Postgres hypertable (optional, no-op elsewhere) ───────────────
async def ensure_hypertables(engine) -> None:
    """Convert market_bars to a TimescaleDB hypertable on Postgres (best-effort).

    No-op on SQLite/other dialects and when the timescaledb extension isn't
    available — the table still works as a plain table, just without the
    time-partitioning optimisation."""
    backend = engine.url.get_backend_name()
    if not backend.startswith("postgresql"):
        return
    from sqlalchemy import text
    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
            await conn.execute(text(
                "SELECT create_hypertable('market_bars', 'date', "
                "if_not_exists => TRUE, migrate_data => TRUE)"
            ))
        logger.info("market_bars is a TimescaleDB hypertable")
    except Exception as e:  # extension missing / insufficient privs — fine
        logger.info("Skipping hypertable setup (timescaledb unavailable): %s", e)


# ── helpers ───────────────────────────────────────────────────────
def _to_naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
