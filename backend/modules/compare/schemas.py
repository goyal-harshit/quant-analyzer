"""Comparison request/response schemas."""

from typing import List, Optional, Dict

from pydantic import BaseModel, Field


class CompareRequest(BaseModel):
    tickers: List[str] = Field(..., min_length=2, max_length=5, description="2-5 NSE tickers")
    period: str = Field(default="1y", description="1m|3m|6m|1y|2y|5y for the return window")


class FactorScores(BaseModel):
    momentum: Optional[float] = None
    quality: Optional[float] = None
    value: Optional[float] = None
    growth: Optional[float] = None
    low_vol: Optional[float] = None
    composite: Optional[float] = None


class AssetComparison(BaseModel):
    ticker: str
    name: str
    sector: Optional[str] = None
    price: float
    change_pct: float

    # Fundamentals
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    roe: Optional[float] = None
    dividend_yield: Optional[float] = None
    debt_equity: Optional[float] = None
    market_cap: Optional[float] = None

    # Price-derived
    returns_period: Optional[float] = None
    volatility: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None

    scores: FactorScores
    spark: List[float] = []      # thinned close series for a sparkline
    source: str = "live"


class BestPick(BaseModel):
    ticker: Optional[str] = None
    value: Optional[float] = None
    reason: str = ""


class CompareResponse(BaseModel):
    assets: List[AssetComparison]
    # Radar-ready: [{ "metric": "Momentum", "INFY": 80, "TCS": 72, ... }, ...]
    radar: List[Dict[str, object]]
    best_momentum: BestPick
    best_quality: BestPick
    best_value: BestPick
    best_risk_adjusted: BestPick
    best_return: BestPick
    recommendation: str
