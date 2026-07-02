"""IPO DB model (plan §5). Registered on the shared Base.metadata."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Float, Integer, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column

from models.database import Base


def _utcnow() -> datetime:
    # Naive UTC — the DateTime column is TIMESTAMP WITHOUT TIME ZONE, and
    # asyncpg rejects tz-aware values for naive columns. (.replace avoids the
    # deprecated datetime.utcnow().)
    return datetime.now(timezone.utc).replace(tzinfo=None)


class IPO(Base):
    __tablename__ = "ipos"

    id:              Mapped[int]             = mapped_column(Integer, primary_key=True)
    company_name:    Mapped[str]             = mapped_column(String(200), nullable=False)
    symbol:          Mapped[Optional[str]]   = mapped_column(String(20), index=True)
    exchange:        Mapped[str]             = mapped_column(String(10), default="NSE")
    ipo_type:        Mapped[str]             = mapped_column(String(20), default="MAINBOARD")
    issue_size_cr:   Mapped[Optional[float]] = mapped_column(Float)
    price_band_low:  Mapped[Optional[float]] = mapped_column(Float)
    price_band_high: Mapped[Optional[float]] = mapped_column(Float)
    lot_size:        Mapped[Optional[int]]   = mapped_column(Integer)
    open_date:       Mapped[Optional[Date]]  = mapped_column(Date)
    close_date:      Mapped[Optional[Date]]  = mapped_column(Date)
    listing_date:    Mapped[Optional[Date]]  = mapped_column(Date)
    listing_price:   Mapped[Optional[float]] = mapped_column(Float)
    gmp:             Mapped[Optional[float]] = mapped_column(Float)
    status:          Mapped[str]             = mapped_column(String(20), default="UPCOMING")
    updated_at:      Mapped[datetime]        = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    def __repr__(self):
        return f"<IPO {self.company_name} {self.status}>"
