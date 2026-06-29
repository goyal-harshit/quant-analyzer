"""
market_store.py — DB tables for the ingest-then-serve market-data store.

These are purpose-built for the "endpoints read from DB, freshness is a column"
architecture (audit §3.1). Unlike the existing FK-coupled `price_data` /
`fundamentals` tables, every row here carries `source` + `fetched_at` (and `as_of`
for point-in-time data), so a served value always knows where it came from and how
fresh it is. Background jobs refresh these tables via the guarded provider chain.

Plain SQLAlchemy columns only (no TimescaleDB-specific DDL) so the same models work
on SQLite (tests) and Postgres (prod); the optional hypertable on `market_bars` is
applied separately for Postgres in `services.market_store.ensure_hypertables`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.database import JSONB, Base, _utcnow


class MarketQuote(Base):
    """Latest snapshot quote per ticker (one row per ticker, upserted)."""

    __tablename__ = "market_quotes"

    ticker:      Mapped[str]   = mapped_column(String(20), primary_key=True)
    price:       Mapped[Optional[float]] = mapped_column(Float)
    prev_close:  Mapped[Optional[float]] = mapped_column(Float)
    change:      Mapped[Optional[float]] = mapped_column(Float)
    change_pct:  Mapped[Optional[float]] = mapped_column(Float)
    open:        Mapped[Optional[float]] = mapped_column(Float)
    day_high:    Mapped[Optional[float]] = mapped_column(Float)
    day_low:     Mapped[Optional[float]] = mapped_column(Float)
    volume:      Mapped[Optional[float]] = mapped_column(Float)
    market_cap:  Mapped[Optional[float]] = mapped_column(Float)
    source:      Mapped[str]   = mapped_column(String(30), default="unknown")
    as_of:       Mapped[Optional[datetime]] = mapped_column(DateTime)
    fetched_at:  Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    # Full original quote dict, so serving from the store preserves every field
    # (name, 52w range, currency, …) the live source returned — no shape regression.
    raw:         Mapped[Optional[dict]] = mapped_column(JSONB)


class MarketBar(Base):
    """Daily OHLCV bar — the time-series store (Postgres: a TimescaleDB hypertable)."""

    __tablename__ = "market_bars"
    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_market_bars_ticker_date"),
        Index("ix_market_bars_ticker_date", "ticker", "date"),
    )

    id:         Mapped[int]   = mapped_column(Integer, primary_key=True)
    ticker:     Mapped[str]   = mapped_column(String(20), nullable=False)
    date:       Mapped[datetime] = mapped_column(DateTime, nullable=False)
    open:       Mapped[Optional[float]] = mapped_column(Float)
    high:       Mapped[Optional[float]] = mapped_column(Float)
    low:        Mapped[Optional[float]] = mapped_column(Float)
    close:      Mapped[Optional[float]] = mapped_column(Float)
    volume:     Mapped[Optional[float]] = mapped_column(Float)
    source:     Mapped[str]   = mapped_column(String(30), default="unknown")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class MarketFundamental(Base):
    """Latest fundamentals snapshot per ticker (one row per ticker, upserted)."""

    __tablename__ = "market_fundamentals"

    ticker:         Mapped[str]   = mapped_column(String(20), primary_key=True)
    pe_ratio:       Mapped[Optional[float]] = mapped_column(Float)
    pb_ratio:       Mapped[Optional[float]] = mapped_column(Float)
    ev_ebitda:      Mapped[Optional[float]] = mapped_column(Float)
    ps_ratio:       Mapped[Optional[float]] = mapped_column(Float)
    roe:            Mapped[Optional[float]] = mapped_column(Float)
    roa:            Mapped[Optional[float]] = mapped_column(Float)
    gross_margin:   Mapped[Optional[float]] = mapped_column(Float)
    ebitda_margin:  Mapped[Optional[float]] = mapped_column(Float)
    net_margin:     Mapped[Optional[float]] = mapped_column(Float)
    revenue_growth: Mapped[Optional[float]] = mapped_column(Float)
    earnings_growth: Mapped[Optional[float]] = mapped_column(Float)
    debt_equity:    Mapped[Optional[float]] = mapped_column(Float)
    dividend_yield: Mapped[Optional[float]] = mapped_column(Float)
    market_cap:     Mapped[Optional[float]] = mapped_column(Float)
    source:         Mapped[str]   = mapped_column(String(30), default="unknown")
    as_of:          Mapped[Optional[datetime]] = mapped_column(DateTime)
    fetched_at:     Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
    raw:            Mapped[Optional[dict]] = mapped_column(JSONB)
