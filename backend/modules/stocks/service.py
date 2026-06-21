"""
Stocks service — business logic for the stocks module.

Delegates data access to the shared services layer (data_service, factor_engine,
seed_data) per PROJECT_PLAN §4. Routers stay thin; all logic lives here.
"""

import json
import logging

import pandas as pd
from fastapi import HTTPException

from services.data_service import data_service, _get_redis
from services.seed_data import search_tickers, get_seed_quote, get_seed_fundamentals
from services.factor_engine import FactorEngine
from services.validation import validate_ticker

logger = logging.getLogger(__name__)
_engine = FactorEngine()


async def search(q: str) -> dict:
    """Comprehensive stock search: Yahoo's market-wide search API (any NSE/BSE
    stock) merged with the local curated list, deduped. Cached per query."""
    q = (q or "").strip()
    if not q:
        return {"query": q, "results": []}

    cache_key = f"stocksearch:{q.lower()}"
    try:
        r = await _get_redis()
        if r:
            cached = await r.get(cache_key)
            if cached:
                return {"query": q, "results": json.loads(cached)}
    except Exception:
        pass

    results: list[dict] = []
    seen: set[str] = set()
    try:
        from services.fast_data import fast_data_service
        for item in await fast_data_service.search(q):
            if item["ticker"] not in seen:
                seen.add(item["ticker"])
                results.append(item)
    except Exception as e:
        logger.warning("Yahoo stock search failed for %r: %s", q, e)

    # Supplement with curated local matches Yahoo may rank lower / miss.
    for item in search_tickers(q):
        t = item.get("ticker")
        if t and t not in seen:
            seen.add(t)
            results.append(item)

    results = results[:15]
    if results:
        try:
            r = await _get_redis()
            if r:
                await r.setex(cache_key, 86400, json.dumps(results))
        except Exception:
            pass
    return {"query": q, "results": results}


async def get_quote(ticker: str, refresh: bool = False) -> dict:
    t = validate_ticker(ticker)
    quote = await data_service.get_quote(t, refresh=refresh)
    if not quote or not quote.get("price"):
        logger.info("Falling back to seed data for %s quote", t)
        quote = get_seed_quote(t)
    return quote


async def get_fundamentals(ticker: str, refresh: bool = False) -> dict:
    t = validate_ticker(ticker)
    data = await data_service.get_fundamentals(t, refresh=refresh)
    if not data:
        data = {"ticker": t}
    if not data.get("sector"):
        data["sector"] = data_service._SECTOR_MAP.get(t)
    if not data.get("industry"):
        data["industry"] = data_service._INDUSTRY_MAP.get(t)
    # Attach absolute (single-stock) factor scores for the radar/composite panel.
    try:
        df = await data_service.get_price_history(t, period="1y", refresh=refresh)
        if df is not None and not df.empty:
            df = df.copy()
            df.columns = [str(c).lower() for c in df.columns]
            if "close" in df.columns:
                from services.fast_data import compute_quant_factors
                f = compute_quant_factors(df, data)
                vol = f.get("volatility_60d")
                low_vol = round(max(0.0, min(100.0, 100.0 - (vol or 30.0))), 1) if vol is not None else None
                data["factor_scores"] = {
                    "momentum": f.get("momentum_score"),
                    "quality": f.get("quality_score"),
                    "value": f.get("value_score"),
                    "growth": f.get("growth_score"),
                    "low_volatility": low_vol,
                    "composite": f.get("composite_score"),
                }
    except Exception as e:  # noqa: BLE001
        logger.warning("factor scores failed for %s: %s", t, e)
    return data


async def get_history(ticker: str, period: str = "1y", interval: str = "1d", refresh: bool = False) -> dict:
    t = validate_ticker(ticker)
    df = await data_service.get_price_history(t, period, interval, refresh=refresh)
    if df.empty:
        df = await data_service.ingest_on_demand(t, period, interval)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No price history for {ticker}")

    df.columns = [c.lower() for c in df.columns]
    # Drop rows with missing OHLC — NaN is not JSON-serializable and would crash
    # the response (and int(NaN) raises). Volume gaps default to 0.
    df = df.dropna(subset=["open", "high", "low", "close"])
    return {
        "ticker": t,
        "data": [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "open": round(float(row["open"]), 2),
                "high": round(float(row["high"]), 2),
                "low": round(float(row["low"]), 2),
                "close": round(float(row["close"]), 2),
                "volume": int(row["volume"]) if pd.notna(row["volume"]) else 0,
            }
            for idx, row in df.iterrows()
        ],
    }


async def get_factors(ticker: str) -> dict:
    t = validate_ticker(ticker)
    prices_df = await data_service.get_price_history(t, period="2y")
    fundamentals = await data_service.get_fundamentals(t)

    if prices_df.empty:
        raise HTTPException(status_code=404, detail=f"Insufficient price data for {ticker}")

    close_prices = prices_df["close"]
    result = {
        "ticker": t,
        "momentum_12_1_raw": None,
        "rsi_14": None,
        "volatility_60d_ann": None,
        "fundamentals": fundamentals,
    }
    if len(close_prices) >= 252:
        result["momentum_12_1_raw"] = round(float((close_prices.iloc[-21] / close_prices.iloc[-252] - 1) * 100), 2)
    if len(close_prices) >= 14:
        result["rsi_14"] = round(_engine.rsi(close_prices), 2)
    if len(close_prices) >= 60:
        daily_rets = close_prices.pct_change().dropna()
        result["volatility_60d_ann"] = round(float(daily_rets.tail(60).std() * (252 ** 0.5) * 100), 2)
    return result


async def get_technicals(ticker: str) -> dict:
    t = validate_ticker(ticker)
    df = await data_service.get_price_history(t, period="1y")
    if df.empty or len(df) < 50:
        raise HTTPException(status_code=404, detail="Insufficient data for technical analysis")

    close = df["close"]
    bb = _engine.bollinger_bands(close)
    return {
        "ticker": t,
        "rsi_14": round(_engine.rsi(close), 2),
        "sma_50": round(float(close.rolling(50).mean().iloc[-1]), 2),
        "sma_200": round(float(close.rolling(200).mean().iloc[-1]), 2) if len(close) >= 200 else None,
        "bollinger": {
            "upper": round(float(bb["upper"].iloc[-1]), 2),
            "middle": round(float(bb["middle"].iloc[-1]), 2),
            "lower": round(float(bb["lower"].iloc[-1]), 2),
        },
        "atr_14": round(float(_engine.atr(df["high"], df["low"], df["close"]).iloc[-1]), 2)
            if all(c in df.columns for c in ["high", "low", "close"]) else None,
    }


async def get_batch_quotes(tickers: str, refresh: bool = False) -> dict:
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    if len(ticker_list) > 100:
        raise HTTPException(status_code=400, detail="Max 100 tickers per batch request")
    return await data_service.get_batch_quotes(ticker_list, refresh=refresh)
