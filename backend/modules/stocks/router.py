"""Stocks router — /api/v1/stocks (thin HTTP layer; logic in service.py)."""

from fastapi import APIRouter, Query

from . import service

router = APIRouter()


@router.get("/search")
async def search_stocks(q: str = Query(..., description="Search by company name or ticker")):
    """Search for stocks by company name or ticker symbol."""
    return service.search(q)


@router.get("/{ticker}/quote")
async def get_quote(ticker: str, refresh: bool = False):
    """Get current price quote for a stock."""
    return await service.get_quote(ticker, refresh=refresh)


@router.get("/{ticker}/fundamentals")
async def get_fundamentals(ticker: str, refresh: bool = False):
    """Get fundamental ratios + factor scores (normalised snake_case keys)."""
    return await service.get_fundamentals(ticker, refresh=refresh)


@router.get("/{ticker}/history")
async def get_price_history(
    ticker: str,
    period: str = Query(default="1y", description="1mo|3mo|6mo|1y|2y|5y|max"),
    interval: str = Query(default="1d", description="1d|1wk|1mo"),
    refresh: bool = False,
):
    """Get OHLCV price history."""
    return await service.get_history(ticker, period, interval, refresh=refresh)


@router.get("/{ticker}/factors")
async def get_factor_scores(ticker: str):
    """Get computed factor scores for a stock."""
    return await service.get_factors(ticker)


@router.get("/{ticker}/technicals")
async def get_technicals(ticker: str):
    """Get technical indicators: RSI, MACD, Bollinger Bands, Moving Averages."""
    return await service.get_technicals(ticker)


@router.get("/batch/quotes")
async def get_batch_quotes(
    tickers: str = Query(..., description="Comma-separated tickers"), refresh: bool = False
):
    """Get quotes for multiple tickers at once."""
    return await service.get_batch_quotes(tickers, refresh=refresh)
