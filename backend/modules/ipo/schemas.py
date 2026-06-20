"""Pydantic schemas for the IPO module."""

from typing import Optional
from pydantic import BaseModel


class IPOItem(BaseModel):
    id: str
    company_name: str
    symbol: Optional[str] = None
    exchange: str = "NSE"
    ipo_type: str = "MAINBOARD"          # MAINBOARD | SME
    issue_size_cr: Optional[float] = None
    price_band_low: Optional[float] = None
    price_band_high: Optional[float] = None
    lot_size: Optional[int] = None
    open_date: Optional[str] = None       # ISO yyyy-mm-dd
    close_date: Optional[str] = None
    listing_date: Optional[str] = None
    listing_price: Optional[float] = None
    current_price: Optional[float] = None
    listing_gain_pct: Optional[float] = None
    gmp: Optional[float] = None            # grey-market premium (₹)
    gmp_pct: Optional[float] = None
    subscription_times: Optional[float] = None
    status: str = "UPCOMING"               # UPCOMING | OPEN | CLOSED | LISTED
