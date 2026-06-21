"""
Trading Simulator DB models. Registered on the shared Base.metadata so
init_db()'s create_all picks them up (imported in main.py).

A portfolio holds cash; every buy/sell is an immutable transaction in the
ledger. Current holdings and P&L are *derived* from the transaction history
(average-cost method) rather than stored, so the books can never drift.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.database import Base


def _utcnow() -> datetime:
    # Naive UTC — the DateTime columns are TIMESTAMP WITHOUT TIME ZONE, and
    # asyncpg rejects tz-aware values for naive columns. (.replace avoids the
    # deprecated datetime.utcnow().)
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SimPortfolio(Base):
    __tablename__ = "sim_portfolios"

    id:               Mapped[int]            = mapped_column(Integer, primary_key=True)
    # Nullable: guest portfolios are anonymous and accessed by id.
    user_id:          Mapped[Optional[int]]  = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name:             Mapped[str]            = mapped_column(String(100), nullable=False)
    starting_capital: Mapped[float]          = mapped_column(Float, nullable=False)
    cash:             Mapped[float]          = mapped_column(Float, nullable=False)
    created_at:       Mapped[datetime]       = mapped_column(DateTime, default=_utcnow)

    transactions: Mapped[list["SimTransaction"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan", order_by="SimTransaction.timestamp"
    )

    def __repr__(self):
        return f"<SimPortfolio {self.id} {self.name}>"


class SimTransaction(Base):
    __tablename__ = "sim_transactions"

    id:            Mapped[int]      = mapped_column(Integer, primary_key=True)
    portfolio_id:  Mapped[int]      = mapped_column(Integer, ForeignKey("sim_portfolios.id"), nullable=False, index=True)
    ticker:        Mapped[str]      = mapped_column(String(20), nullable=False, index=True)
    side:          Mapped[str]      = mapped_column(String(4), nullable=False)   # "BUY" | "SELL"
    quantity:      Mapped[float]    = mapped_column(Float, nullable=False)
    price:         Mapped[float]    = mapped_column(Float, nullable=False)        # execution price
    fees:          Mapped[float]    = mapped_column(Float, default=0.0)
    # Realized P&L is recorded on SELL legs only (0 on BUY).
    realized_pnl:  Mapped[float]    = mapped_column(Float, default=0.0)
    timestamp:     Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    portfolio: Mapped["SimPortfolio"] = relationship(back_populates="transactions")

    def __repr__(self):
        return f"<SimTransaction {self.side} {self.quantity} {self.ticker} @ {self.price}>"
