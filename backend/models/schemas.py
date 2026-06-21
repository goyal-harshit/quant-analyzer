"""Pydantic schemas — request/response models"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── STOCK ─────────────────────────────────────────────────────────
class StockBase(BaseModel):
    ticker: str
    name: str
    sector: str
    exchange: str = "NSE"

class StockPrice(BaseModel):
    ticker: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: int

class Fundamentals(BaseModel):
    ticker: str
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    ps_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    roe: Optional[float] = None
    roce: Optional[float] = None
    roa: Optional[float] = None
    net_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    gross_margin: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    debt_equity: Optional[float] = None
    interest_coverage: Optional[float] = None
    revenue_growth: Optional[float] = None
    dividend_yield: Optional[float] = None
    market_cap: Optional[float] = None
    book_value: Optional[float] = None
    face_value: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    exchange: Optional[str] = "NSE"

class StockQuote(BaseModel):
    ticker: str
    name: str
    sector: str
    price: float
    change: float
    change_pct: float
    volume: int
    market_cap: Optional[float] = None
    prev_close: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None

class StockDetail(StockBase):
    price: float
    change_pct: float
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]
    roe: Optional[float]
    revenue_growth: Optional[float]
    debt_equity: Optional[float]
    factor_scores: Optional["FactorScoreOut"] = None

class FactorScoreOut(BaseModel):
    ticker: str
    date: datetime
    momentum: Optional[float]
    quality: Optional[float]
    value: Optional[float]
    growth: Optional[float]
    size: Optional[float]
    low_volatility: Optional[float]
    composite: Optional[float]


# ── SCREENER ──────────────────────────────────────────────────────
class ScreenerFilter(BaseModel):
    sector: Optional[str] = None
    min_pe: Optional[float] = None
    max_pe: Optional[float] = None
    min_pb: Optional[float] = None
    max_pb: Optional[float] = None
    min_roe: Optional[float] = None
    min_momentum: Optional[float] = None
    min_quality: Optional[float] = None
    min_value: Optional[float] = None
    min_growth: Optional[float] = None
    min_composite: Optional[float] = None
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    universe: str = Field(default="NIFTY500", description="NIFTY50|NIFTY200|NIFTY500|BSE500")
    tickers: list[str] = Field(default_factory=list, description="Custom ticker list (overrides universe)")
    sort_by: str = Field(default="composite", description="Field to sort by")
    sort_dir: str = Field(default="desc", description="asc|desc")
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    refresh: Optional[bool] = False

class ScreenerResult(BaseModel):
    ticker: str
    name: str
    sector: str
    price: float
    change_pct: float
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]
    roe: Optional[float]
    revenue_growth: Optional[float]
    momentum_score: Optional[float]
    quality_score: Optional[float]
    value_score: Optional[float]
    growth_score: Optional[float]
    composite_score: Optional[float]
    market_cap: Optional[float]

class ScreenerResponse(BaseModel):
    results: List[ScreenerResult]
    total: int
    filtered: int


# ── PORTFOLIO ─────────────────────────────────────────────────────
class PositionCreate(BaseModel):
    ticker: str
    quantity: float = Field(gt=0)
    avg_cost: float = Field(gt=0)
    notes: Optional[str] = None

class PositionOut(BaseModel):
    id: int
    ticker: str
    quantity: float
    avg_cost: float
    current_price: Optional[float]
    current_value: Optional[float]
    cost_basis: float
    pnl: Optional[float]
    pnl_pct: Optional[float]
    factor_score: Optional[float]
    sector: Optional[str]

class PortfolioCreate(BaseModel):
    name: str
    currency: str = "INR"
    benchmark: str = "NIFTY50"
    description: Optional[str] = None

class PortfolioSummary(BaseModel):
    id: int
    name: str
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    position_count: int

class PortfolioOut(BaseModel):
    id: int
    name: str
    currency: str
    benchmark: str
    positions: List[PositionOut]
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_pct: float
    beta: Optional[float]
    sharpe: Optional[float]
    volatility: Optional[float]
    max_drawdown: Optional[float]


# ── BACKTEST ──────────────────────────────────────────────────────
class BacktestRequest(BaseModel):
    strategy_name: str
    universe: str = "NIFTY500"
    start_date: str = "2020-01-01"
    end_date: str = "2025-06-01"
    rebalance_freq: str = Field(default="quarterly", description="monthly|quarterly|semi-annual|annual")
    top_n: int = Field(default=20, ge=5, le=100, description="Number of stocks to hold")
    factor_weights: dict = Field(default={
        "momentum": 0.25, "quality": 0.25, "value": 0.20,
        "growth": 0.20, "low_volatility": 0.10
    })
    transaction_cost: float = Field(default=0.001, description="One-way transaction cost as fraction")
    benchmark: str = "NIFTY50"

class BacktestDataPoint(BaseModel):
    date: str
    portfolio_value: float
    benchmark_value: float
    active_return: float

class BacktestMetrics(BaseModel):
    total_return: float
    annualised_return: float
    benchmark_return: float
    alpha: float
    beta: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    win_rate: float
    avg_monthly_return: float
    volatility_ann: float

class BacktestResponse(BaseModel):
    request: BacktestRequest
    metrics: BacktestMetrics
    equity_curve: List[BacktestDataPoint]
    monthly_returns: List[dict]
    top_holdings_last: List[dict]
    turnover_avg: float


# ── MACRO ─────────────────────────────────────────────────────────
class MacroIndicator(BaseModel):
    name: str
    value: float
    date: str
    unit: str
    source: str
    yoy_change: Optional[float] = None

class MacroResponse(BaseModel):
    repo_rate: List[dict]
    cpi: List[dict]
    gdp_growth: List[dict]
    usd_inr: List[dict]
    fii_flows: List[dict]
    dii_flows: List[dict]
    credit_growth: List[dict]
    current_indicators: List[MacroIndicator]


class WatchlistOut(BaseModel):
    id: int
    name: str
    tickers: list[str]
    created_at: datetime


class AlertCreate(BaseModel):
    ticker: str
    condition_type: str = Field(..., description="price_above|price_below|pct_change_above|pct_change_below")
    threshold: float = Field(..., description="Threshold value for the condition")


class AlertOut(BaseModel):
    id: int
    ticker: str
    condition_type: str
    threshold: float
    status: str
    created_at: datetime


class FactorModelRequest(BaseModel):
    name: str
    factor_weights: dict = Field(default={
        "momentum": 0.25, "quality": 0.25, "value": 0.20,
        "growth": 0.20, "low_volatility": 0.10
    })
    universe: str = Field(default="NIFTY50")
    tickers: list[str] = Field(default_factory=list, description="Custom ticker list (overrides universe)")
    filters: Optional[dict] = None


class StrategyRule(BaseModel):
    type: str = Field(..., description="factor|technical|fundamental")
    field: str
    operator: str = Field(..., description="gt|lt|gte|lte|between")
    value: float
    weight: float = 1.0


class StrategyRequest(BaseModel):
    name: str
    rules: list[StrategyRule]
    universe: str = "NIFTY50"
    start_date: str = "2022-01-01"
    end_date: str = "2025-12-31"
    rebalance_freq: str = Field(default="quarterly", description="monthly|quarterly|semi-annual|annual")
    top_n: int = Field(default=20, ge=5, le=100)
    transaction_cost: float = Field(default=0.001)


class WatchlistCreate(BaseModel):
    name: str
    tickers: Optional[list[str]] = None


class MarketSummary(BaseModel):
    nifty50: dict
    sensex: dict
    bank_nifty: dict
    vix: float


# ── AI ────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str = Field(..., description="user|assistant")
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context_ticker: Optional[str] = None
    provider: str = "ollama"
    model: Optional[str] = None
    api_key: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    model: str
    tokens_used: int

class EarningsSummaryRequest(BaseModel):
    ticker: str
    period: str = "latest"

class AIReportRequest(BaseModel):
    ticker: str
    report_type: str = Field(default="full", description="full|brief|risk|growth|value")

class AIReportResponse(BaseModel):
    ticker: str
    report_type: str
    content: str
    model: str
    generated_at: datetime
    disclaimer: str = "For educational purposes only. Not investment advice."


# ── AUTH ──────────────────────────────────────────────────────────
class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    plan: str
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
