"""
Database setup — PostgreSQL + TimescaleDB
Async SQLAlchemy with connection pooling
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Boolean, Text, Index, Date, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB

# Use JSONB on PostgreSQL (indexable, native) but fall back to generic JSON on
# other dialects (e.g. SQLite for local/dev/test) so the models are portable.
JSONB = _PG_JSONB().with_variant(JSON(), "sqlite")
from datetime import datetime, timezone
from typing import Optional
import os


def _utcnow() -> datetime:
    """Timezone-aware UTC now. Replaces the deprecated datetime.utcnow."""
    return datetime.now(timezone.utc)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://quantai:quantai_pass@localhost:5432/quantai_db"
)
# Render provides postgresql:// but asyncpg requires postgresql+asyncpg://
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# pool_size/max_overflow only apply to pooled dialects (Postgres). SQLite's
# default pool rejects them, so add them conditionally for portability.
_engine_kwargs = {"echo": False}
if DATABASE_URL.startswith("postgresql"):
    _engine_kwargs.update(pool_size=10, max_overflow=20, pool_pre_ping=True)
engine = create_async_engine(DATABASE_URL, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class StockMaster(Base):
    __tablename__ = "stock_master"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True)
    ticker:      Mapped[str]           = mapped_column(String(20), unique=True, index=True, nullable=False)
    name:        Mapped[str]           = mapped_column(String(200), nullable=False)
    sector:      Mapped[str]           = mapped_column(String(100))
    industry:    Mapped[Optional[str]] = mapped_column(String(100))
    exchange:    Mapped[str]           = mapped_column(String(10), default="NSE")
    isin:        Mapped[Optional[str]] = mapped_column(String(20))
    market_cap:  Mapped[Optional[float]] = mapped_column(Float)
    is_active:   Mapped[bool]          = mapped_column(Boolean, default=True)
    created_at:  Mapped[datetime]      = mapped_column(DateTime, default=_utcnow)
    updated_at:  Mapped[datetime]      = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    price_data:     Mapped[list["PriceData"]]    = relationship(back_populates="stock")
    fundamentals:   Mapped[list["Fundamentals"]] = relationship(back_populates="stock")
    factor_scores:  Mapped[list["FactorScore"]] = relationship(back_populates="stock")

    def __repr__(self):
        return f"<StockMaster {self.ticker}>"


class PriceData(Base):
    __tablename__ = "price_data"
    __table_args__ = (
        Index("ix_price_data_ticker_date", "ticker", "date"),
        # Prevents duplicate bars from concurrent ingestion (check-then-act race).
        UniqueConstraint("ticker", "date", name="uq_price_data_ticker_date"),
    )

    id:       Mapped[int]   = mapped_column(Integer, primary_key=True)
    ticker:   Mapped[str]   = mapped_column(String(20), ForeignKey("stock_master.ticker"), nullable=False)
    date:     Mapped[datetime] = mapped_column(DateTime, nullable=False)
    open:     Mapped[float] = mapped_column(Float)
    high:     Mapped[float] = mapped_column(Float)
    low:      Mapped[float] = mapped_column(Float)
    close:    Mapped[float] = mapped_column(Float)
    adj_close: Mapped[float] = mapped_column(Float)
    volume:   Mapped[int]   = mapped_column(Integer)

    stock: Mapped["StockMaster"] = relationship(back_populates="price_data")

    def __repr__(self):
        return f"<PriceData {self.ticker} {self.date}>"


class Fundamentals(Base):
    __tablename__ = "fundamentals"
    __table_args__ = (
        # One fundamentals row per (ticker, period) — guards the upsert race.
        UniqueConstraint("ticker", "period", name="uq_fundamentals_ticker_period"),
    )

    id:             Mapped[int]            = mapped_column(Integer, primary_key=True)
    ticker:         Mapped[str]            = mapped_column(String(20), ForeignKey("stock_master.ticker"), nullable=False)
    period:         Mapped[str]            = mapped_column(String(20))
    period_end:     Mapped[datetime]       = mapped_column(DateTime)
    pe_ratio:       Mapped[Optional[float]] = mapped_column(Float)
    pb_ratio:       Mapped[Optional[float]] = mapped_column(Float)
    ev_ebitda:      Mapped[Optional[float]] = mapped_column(Float)
    ps_ratio:       Mapped[Optional[float]] = mapped_column(Float)
    roe:            Mapped[Optional[float]] = mapped_column(Float)
    roa:            Mapped[Optional[float]] = mapped_column(Float)
    roic:           Mapped[Optional[float]] = mapped_column(Float)
    gross_margin:   Mapped[Optional[float]] = mapped_column(Float)
    ebitda_margin:  Mapped[Optional[float]] = mapped_column(Float)
    net_margin:     Mapped[Optional[float]] = mapped_column(Float)
    revenue_growth: Mapped[Optional[float]] = mapped_column(Float)
    eps_growth:     Mapped[Optional[float]] = mapped_column(Float)
    debt_equity:    Mapped[Optional[float]] = mapped_column(Float)
    current_ratio:  Mapped[Optional[float]] = mapped_column(Float)
    fcf_yield:      Mapped[Optional[float]] = mapped_column(Float)
    revenue:        Mapped[Optional[float]] = mapped_column(Float)
    ebitda:         Mapped[Optional[float]] = mapped_column(Float)
    net_profit:     Mapped[Optional[float]] = mapped_column(Float)
    total_debt:     Mapped[Optional[float]] = mapped_column(Float)
    created_at:     Mapped[datetime]        = mapped_column(DateTime, default=_utcnow)

    stock: Mapped["StockMaster"] = relationship(back_populates="fundamentals")

    def __repr__(self):
        return f"<Fundamentals {self.ticker} {self.period}>"


class FactorScore(Base):
    __tablename__ = "factor_scores"
    __table_args__ = (
        Index("ix_factor_scores_ticker_date", "ticker", "date"),
        # One score row per (ticker, date) — guards the upsert race.
        UniqueConstraint("ticker", "date", name="uq_factor_scores_ticker_date"),
    )

    id:              Mapped[int]   = mapped_column(Integer, primary_key=True)
    ticker:          Mapped[str]   = mapped_column(String(20), ForeignKey("stock_master.ticker"), nullable=False)
    date:            Mapped[datetime] = mapped_column(DateTime, nullable=False)
    momentum_score:  Mapped[Optional[float]] = mapped_column(Float)
    quality_score:   Mapped[Optional[float]] = mapped_column(Float)
    value_score:     Mapped[Optional[float]] = mapped_column(Float)
    growth_score:    Mapped[Optional[float]] = mapped_column(Float)
    size_score:      Mapped[Optional[float]] = mapped_column(Float)
    low_vol_score:   Mapped[Optional[float]] = mapped_column(Float)
    composite_score: Mapped[Optional[float]] = mapped_column(Float)
    momentum_12_1:   Mapped[Optional[float]] = mapped_column(Float)
    momentum_3_1:    Mapped[Optional[float]] = mapped_column(Float)
    momentum_6_1:    Mapped[Optional[float]] = mapped_column(Float)
    volatility_60d:  Mapped[Optional[float]] = mapped_column(Float)
    created_at:      Mapped[datetime]        = mapped_column(DateTime, default=_utcnow)

    stock: Mapped["StockMaster"] = relationship(back_populates="factor_scores")

    def __repr__(self):
        return f"<FactorScore {self.ticker} {self.date}>"


class User(Base):
    __tablename__ = "users"

    id:         Mapped[int]  = mapped_column(Integer, primary_key=True)
    email:      Mapped[str]  = mapped_column(String(255), unique=True, nullable=False)
    hashed_pw:  Mapped[str]  = mapped_column(String(255))
    plan:       Mapped[str]  = mapped_column(String(20), default="free")
    role:       Mapped[str]  = mapped_column(String(20), default="user", server_default="user")  # user | admin
    is_active:  Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    portfolios:     Mapped[list["Portfolio"]] = relationship(back_populates="user")
    watchlists:     Mapped[list["Watchlist"]] = relationship(back_populates="user")
    alerts:         Mapped[list["Alert"]] = relationship(back_populates="user")
    strategies:     Mapped[list["Strategy"]] = relationship(back_populates="user")
    backtest_runs:  Mapped[list["BacktestRun"]] = relationship(back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"


class Portfolio(Base):
    __tablename__ = "portfolios"

    id:          Mapped[int]  = mapped_column(Integer, primary_key=True)
    user_id:     Mapped[int]  = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name:        Mapped[str]  = mapped_column(String(100), nullable=False)
    currency:    Mapped[str]  = mapped_column(String(3), default="INR")
    benchmark:   Mapped[str]  = mapped_column(String(20), default="NIFTY50")
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    user:      Mapped["User"]        = relationship(back_populates="portfolios")
    positions: Mapped[list["Position"]] = relationship(back_populates="portfolio")

    def __repr__(self):
        return f"<Portfolio {self.name}>"


class Position(Base):
    __tablename__ = "positions"

    id:           Mapped[int]   = mapped_column(Integer, primary_key=True)
    portfolio_id: Mapped[int]   = mapped_column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ticker:       Mapped[str]   = mapped_column(String(20), nullable=False)
    quantity:     Mapped[float] = mapped_column(Float, nullable=False)
    avg_cost:     Mapped[float] = mapped_column(Float, nullable=False)
    date_added:   Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    notes:        Mapped[Optional[str]] = mapped_column(Text)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="positions")

    def __repr__(self):
        return f"<Position {self.ticker} x{self.quantity}>"


class Watchlist(Base):
    __tablename__ = "watchlists"

    id:         Mapped[int]   = mapped_column(Integer, primary_key=True)
    user_id:    Mapped[int]   = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name:       Mapped[str]   = mapped_column(String(100), nullable=False)
    tickers:    Mapped[list]  = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="watchlists")

    def __repr__(self):
        return f"<Watchlist {self.name}>"


class Alert(Base):
    __tablename__ = "alerts"

    id:           Mapped[int]  = mapped_column(Integer, primary_key=True)
    user_id:      Mapped[int]  = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    ticker:       Mapped[str]  = mapped_column(String(20), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(50))
    threshold:    Mapped[float] = mapped_column(Float)
    status:       Mapped[str]  = mapped_column(String(20), default="active")
    created_at:   Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="alerts")

    def __repr__(self):
        return f"<Alert {self.ticker} {self.condition_type} {self.threshold}>"


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id:          Mapped[int]  = mapped_column(Integer, primary_key=True)
    ticker:      Mapped[str]  = mapped_column(String(20), nullable=False)
    report_type: Mapped[str]  = mapped_column(String(50))
    content:     Mapped[str]  = mapped_column(Text, nullable=False)
    model_used:  Mapped[str]  = mapped_column(String(50))
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    def __repr__(self):
        return f"<GeneratedReport {self.ticker} {self.report_type}>"


class Strategy(Base):
    __tablename__ = "strategies"

    id:          Mapped[int]  = mapped_column(Integer, primary_key=True)
    user_id:     Mapped[int]  = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name:        Mapped[str]  = mapped_column(String(100), nullable=False)
    rules_json:  Mapped[str]  = mapped_column(Text, default="{}")
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at:  Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    user: Mapped["User"] = relationship(back_populates="strategies")
    backtest_runs: Mapped[list["BacktestRun"]] = relationship(back_populates="strategy")

    def __repr__(self):
        return f"<Strategy {self.name}>"


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id:          Mapped[int]  = mapped_column(Integer, primary_key=True)
    strategy_id: Mapped[int]  = mapped_column(Integer, ForeignKey("strategies.id"), nullable=False)
    user_id:     Mapped[int]  = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    start_date:  Mapped[Date] = mapped_column(Date, nullable=False)
    end_date:    Mapped[Date] = mapped_column(Date, nullable=False)
    results_json: Mapped[str] = mapped_column(Text, default="{}")
    status:      Mapped[str]  = mapped_column(String(20), default="pending")
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    strategy: Mapped["Strategy"] = relationship(back_populates="backtest_runs")
    user: Mapped["User"] = relationship(back_populates="backtest_runs")

    def __repr__(self):
        return f"<BacktestRun {self.id} {self.status}>"


async def init_db():
    """Ensure the schema exists. In dev/test (DB_AUTO_CREATE=true, the default) this
    uses create_all for convenience. In production set DB_AUTO_CREATE=false so
    Alembic migrations are the single source of truth (applied on deploy) and a
    stray create_all can't mask a missing migration."""
    if os.getenv("DB_AUTO_CREATE", "true").lower() in ("0", "false", "no"):
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
