"""Stocks Router — Individual stock data endpoints"""

import logging

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from services.data_service import data_service
from services.seed_data import search_tickers, get_seed_quote, get_seed_fundamentals
from services.factor_engine import FactorEngine
import pandas as pd

logger = logging.getLogger(__name__)

router = APIRouter()
engine = FactorEngine()


@router.get("/search")
async def search_stocks(q: str = Query(..., description="Search by company name or ticker")):
    """Search for stocks by company name or ticker symbol."""
    results = search_tickers(q)
    return {"query": q, "results": results}


@router.get("/{ticker}/quote")
async def get_quote(ticker: str, refresh: bool = False):
    """Get current price quote for a stock."""
    t = ticker.upper()
    quote = await data_service.get_quote(t, refresh=refresh)
    if not quote or not quote.get("price"):
        logger.info("Falling back to seed data for %s quote", t)
        quote = get_seed_quote(t)
    return quote


@router.get("/{ticker}/fundamentals")
async def get_fundamentals(ticker: str, refresh: bool = False):
    """Get fundamental ratios for a stock."""
    t = ticker.upper()
    data = await data_service.get_fundamentals(t, refresh=refresh)
    if not data:
        logger.info("Falling back to seed data for %s fundamentals", t)
        data = get_seed_fundamentals(t)
    if not data.get("sector"):
        data["sector"] = data_service._SECTOR_MAP.get(t)
    if not data.get("industry"):
        data["industry"] = data_service._INDUSTRY_MAP.get(t)
    return data


@router.get("/{ticker}/history")
async def get_price_history(
    ticker: str,
    period: str = Query(default="1y", description="1mo|3mo|6mo|1y|2y|5y|max"),
    interval: str = Query(default="1d", description="1d|1wk|1mo"),
    refresh: bool = False,
):
    """Get OHLCV price history."""
    t = ticker.upper()
    df = await data_service.get_price_history(t, period, interval, refresh=refresh)
    if df.empty:
        # Trigger on-demand ingestion
        df = await data_service.ingest_on_demand(t, period, interval)
        
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No price history for {ticker}")

    # Normalize headers to lowercase
    df.columns = [c.lower() for c in df.columns]

    return {
        "ticker": t,
        "data": [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "open": round(row["open"], 2),
                "high": round(row["high"], 2),
                "low": round(row["low"], 2),
                "close": round(row["close"], 2),
                "volume": int(row["volume"]),
            }
            for idx, row in df.iterrows()
        ],
    }


@router.get("/{ticker}/factors")
async def get_factor_scores(ticker: str):
    """Get computed factor scores for a stock."""
    prices_df = await data_service.get_price_history(ticker.upper(), period="2y")
    fundamentals = await data_service.get_fundamentals(ticker.upper())

    if prices_df.empty:
        raise HTTPException(status_code=404, detail=f"Insufficient price data for {ticker}")

    close_prices = prices_df["close"]
    result = {
        "ticker": ticker.upper(),
        "momentum_12_1_raw": None,
        "rsi_14": None,
        "volatility_60d_ann": None,
        "fundamentals": fundamentals,
    }

    if len(close_prices) >= 252:
        result["momentum_12_1_raw"] = round(
            float((close_prices.iloc[-21] / close_prices.iloc[-252] - 1) * 100), 2
        )
    if len(close_prices) >= 14:
        result["rsi_14"] = round(engine.rsi(close_prices), 2)
    if len(close_prices) >= 60:
        daily_rets = close_prices.pct_change().dropna()
        result["volatility_60d_ann"] = round(
            float(daily_rets.tail(60).std() * (252 ** 0.5) * 100), 2
        )

    return result


@router.get("/{ticker}/technicals")
async def get_technicals(ticker: str):
    """Get technical indicators: RSI, MACD, Bollinger Bands, Moving Averages."""
    df = await data_service.get_price_history(ticker.upper(), period="1y")
    if df.empty or len(df) < 50:
        raise HTTPException(status_code=404, detail="Insufficient data for technical analysis")

    close = df["close"]
    bb = engine.bollinger_bands(close)

    return {
        "ticker": ticker.upper(),
        "rsi_14": round(engine.rsi(close), 2),
        "sma_50": round(float(close.rolling(50).mean().iloc[-1]), 2),
        "sma_200": round(float(close.rolling(200).mean().iloc[-1]), 2) if len(close) >= 200 else None,
        "bollinger": {
            "upper": round(float(bb["upper"].iloc[-1]), 2),
            "middle": round(float(bb["middle"].iloc[-1]), 2),
            "lower": round(float(bb["lower"].iloc[-1]), 2),
        },
        "atr_14": round(float(engine.atr(df["high"], df["low"], df["close"]).iloc[-1]), 2)
            if all(c in df.columns for c in ["high", "low", "close"]) else None,
    }


@router.get("/batch/quotes")
async def get_batch_quotes(tickers: str = Query(..., description="Comma-separated tickers"), refresh: bool = False):
    """Get quotes for multiple tickers at once."""
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    if len(ticker_list) > 100:
        raise HTTPException(status_code=400, detail="Max 100 tickers per batch request")
    quotes = await data_service.get_batch_quotes(ticker_list, refresh=refresh)
    return quotes
