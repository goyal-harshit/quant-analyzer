"""Trading Simulator request/response schemas."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class CreatePortfolioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    starting_capital: float = Field(default=100000.0, gt=0, description="Virtual starting cash in INR")


class TradeRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    side: TradeSide
    quantity: float = Field(..., gt=0)
    # Optional limit price; if omitted the order executes at the live market price.
    price: Optional[float] = Field(default=None, gt=0)


class Holding(BaseModel):
    ticker: str
    name: str
    quantity: float
    avg_cost: float
    current_price: float
    market_value: float
    invested: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    change_pct: float          # the stock's own daily move
    weight_pct: float          # share of portfolio market value
    source: str = "live"


class PortfolioState(BaseModel):
    id: int
    name: str
    starting_capital: float
    cash: float
    invested: float
    market_value: float        # value of holdings at live prices
    total_value: float         # cash + market_value
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float           # total_value - starting_capital
    total_pnl_pct: float
    holdings: List[Holding]
    holdings_count: int
    created_at: datetime


class TransactionOut(BaseModel):
    id: int
    ticker: str
    side: str
    quantity: float
    price: float
    fees: float
    realized_pnl: float
    timestamp: datetime


class EquityPoint(BaseModel):
    date: str
    value: float


class Performance(BaseModel):
    starting_capital: float
    current_value: float
    total_return_pct: float
    realized_pnl: float
    unrealized_pnl: float
    trades_total: int
    sells_closed: int
    win_rate: float            # 0-1, over realizing (SELL) trades
    avg_win: float
    avg_loss: float
    best_trade: float
    worst_trade: float
    max_drawdown_pct: float
    sharpe_ratio: float
    equity_curve: List[EquityPoint]
