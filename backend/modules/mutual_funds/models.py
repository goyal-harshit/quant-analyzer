"""
Mutual Fund DB models (plan §5). Registered on the shared Base.metadata so
init_db()'s create_all picks them up. The MF endpoints are primarily served
live from mfapi.in + Redis cache; these tables exist for optional persistence
and to keep the schema aligned with PROJECT_PLAN.md.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Integer, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column

from models.database import Base


class MFScheme(Base):
    __tablename__ = "mf_schemes"

    scheme_code:  Mapped[int]           = mapped_column(Integer, primary_key=True)
    scheme_name:  Mapped[str]           = mapped_column(String(300), nullable=False, index=True)
    fund_house:   Mapped[Optional[str]] = mapped_column(String(150))
    scheme_type:  Mapped[Optional[str]] = mapped_column(String(100))
    category:     Mapped[Optional[str]] = mapped_column(String(150))
    updated_at:   Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MFScheme {self.scheme_code} {self.scheme_name[:30]}>"


class MFNav(Base):
    __tablename__ = "mf_nav"

    id:           Mapped[int]   = mapped_column(Integer, primary_key=True)
    scheme_code:  Mapped[int]   = mapped_column(Integer, index=True, nullable=False)
    date:         Mapped[Date]  = mapped_column(Date, nullable=False)
    nav:          Mapped[float] = mapped_column(Float, nullable=False)

    def __repr__(self):
        return f"<MFNav {self.scheme_code} {self.date} {self.nav}>"
