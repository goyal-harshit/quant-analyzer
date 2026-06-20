"""Pydantic schemas for the Mutual Funds module."""

from typing import Optional
from pydantic import BaseModel


class MFSearchResult(BaseModel):
    scheme_code: int
    scheme_name: str
    fund_house: Optional[str] = None
    category: Optional[str] = None


class NavPoint(BaseModel):
    date: str          # ISO yyyy-mm-dd
    nav: float


class MFMeta(BaseModel):
    scheme_code: int
    scheme_name: str
    fund_house: Optional[str] = None
    scheme_type: Optional[str] = None
    scheme_category: Optional[str] = None


class MFDetail(BaseModel):
    meta: MFMeta
    latest_nav: Optional[float] = None
    latest_date: Optional[str] = None
    nav_history: list[NavPoint] = []


class MFReturns(BaseModel):
    scheme_code: int
    scheme_name: str
    latest_nav: Optional[float] = None
    ret_1m: Optional[float] = None
    ret_3m: Optional[float] = None
    ret_6m: Optional[float] = None
    ret_1y: Optional[float] = None
    cagr_3y: Optional[float] = None
    cagr_5y: Optional[float] = None
    cagr_since_inception: Optional[float] = None


class MFRisk(BaseModel):
    scheme_code: int
    scheme_name: str
    volatility_pct: Optional[float] = None      # annualised std dev of daily returns
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    risk_grade: Optional[str] = None


class SIPRequest(BaseModel):
    monthly_amount: float
    years: float
    expected_return: float = 12.0   # annual %
    annual_step_up: float = 0.0     # % yearly increase in SIP amount


class SIPResponse(BaseModel):
    monthly_amount: float
    years: float
    expected_return: float
    total_invested: float
    future_value: float
    estimated_gain: float
    wealth_multiple: float


class CompareRequest(BaseModel):
    scheme_codes: list[int]
