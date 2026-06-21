"""Sector analytics schemas."""

from typing import Dict, List, Optional

from pydantic import BaseModel


class ComponentStock(BaseModel):
    ticker: str
    name: str
    price: float
    change_pct: float
    composite_score: Optional[float] = None


class SectorPerf(BaseModel):
    name: str
    change_pct: float                 # avg 1-day move of members
    week_pct: Optional[float] = None
    month_pct: Optional[float] = None
    avg_pe: Optional[float] = None
    avg_roe: Optional[float] = None
    momentum_score: Optional[float] = None
    composite_score: Optional[float] = None
    stock_count: int
    advancers: int
    decliners: int
    top_gainer: Optional[ComponentStock] = None
    top_loser: Optional[ComponentStock] = None
    components: List[ComponentStock] = []


class Sentiment(BaseModel):
    bullish: int
    neutral: int
    bearish: int


class SectorsResponse(BaseModel):
    sectors: List[SectorPerf]         # sorted by change_pct desc
    heatmap: Dict[str, float]         # sector -> 1d change_pct
    sentiment: Sentiment
    top_gainers: List[ComponentStock]
    top_losers: List[ComponentStock]
