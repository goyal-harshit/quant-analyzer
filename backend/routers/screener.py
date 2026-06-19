"""Screener Router — Multi-factor stock screening (parallel-optimized).
All data fetched in a single batch, factor scores from Redis cache or computed once.
3 sequential rounds → 1 parallel round = ~3x faster for same universe size.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
import pandas as pd

from models.schemas import ScreenerFilter, ScreenerResponse, ScreenerResult
from services.data_service import data_service, _gather_limited
from services.factor_engine import FactorEngine
from services.seed_data import DEFAULT_TICKERS, get_seed_screener_results, get_seed_sectors, get_seed_fundamentals, get_seed_quote
from services.cache_service import cache, TTL_FACTOR_SCORES

logger = logging.getLogger(__name__)

router = APIRouter()
engine = FactorEngine()


@router.post("", response_model=ScreenerResponse)
async def screen_stocks(filters: ScreenerFilter):
    """Screen the universe using factor and fundamental filters.
    All data fetched in ONE parallel batch for minimum latency.
    """
    universe = filters.tickers if filters.tickers and len(filters.tickers) > 0 else DEFAULT_TICKERS

    # Single parallel batch: fundamentals + history + quotes all at once
    all_coros = []
    for t in universe:
        all_coros.append(data_service.get_fundamentals(t))
    for t in universe:
        all_coros.append(data_service.get_price_history(t, period="1y"))
    for t in universe:
        all_coros.append(data_service.get_quote(t))

    all_results = await _gather_limited(all_coros, limit=20)
    n = len(universe)
    fund_results = all_results[:n]
    hist_results = all_results[n:2*n]
    quote_results = all_results[2*n:]

    fundamentals_list = []
    for ticker, fund in zip(universe, fund_results):
        if fund:
            fund = dict(fund) if isinstance(fund, dict) else fund
            if isinstance(fund, dict):
                fund["ticker"] = ticker
                if not fund.get("sector"):
                    fund["sector"] = data_service._SECTOR_MAP.get(ticker)
                fundamentals_list.append(fund)
                continue
        sd = get_seed_fundamentals(ticker)
        sd["ticker"] = ticker
        sd["source"] = "seed"
        fundamentals_list.append(sd)

    price_histories = {}
    for ticker, df in zip(universe, hist_results):
        if df is not None and not df.empty:
            price_histories[ticker] = df["close"]

    if not fundamentals_list:
        raise HTTPException(status_code=503, detail="Unable to fetch universe data")

    fund_df = pd.DataFrame(fundamentals_list).set_index("ticker")
    price_matrix = pd.DataFrame(price_histories)

    # Compute factor scores — prefer Redis cache per ticker, compute missing
    factor_cache_keys = {t: f"fs_{t}" for t in fund_df.index}
    cached_factors = {}
    keys_to_fetch = list(factor_cache_keys.values())
    try:
        from services.cache_service import cache as _cache
        cached_values = await asyncio.gather(*[_cache.get(k) for k in keys_to_fetch], return_exceptions=True)
        for t, cv in zip(fund_df.index, cached_values):
            if cv and not isinstance(cv, Exception):
                try:
                    cached_factors[t] = json.loads(cv)
                except Exception:
                    pass
    except Exception:
        pass

    momentum_scores = engine.compute_momentum_score(price_matrix) if not price_matrix.empty else pd.Series(dtype=float)
    quality_scores = engine.compute_quality_score(fund_df)
    value_scores = engine.compute_value_score(fund_df)
    growth_scores = engine.compute_growth_score(fund_df)
    low_vol_scores = engine.compute_low_vol_score(price_matrix) if not price_matrix.empty else pd.Series(dtype=float)

    composite_scores = engine.compute_composite(
        momentum_scores, quality_scores, value_scores, growth_scores, low_vol_scores
    )

    quote_map = dict(zip(universe, quote_results))

    results = []
    for ticker in fund_df.index:
        fund = fund_df.loc[ticker]
        quote = quote_map.get(ticker)
        if not quote or not isinstance(quote, dict):
            quote = get_seed_quote(ticker)

        prev_close = quote.get("prev_close") or quote.get("price", 0) or 0
        price = quote.get("price") or 0

        cache_hit = cached_factors.get(ticker)

        def n(v):
            return None if (isinstance(v, float) and pd.isna(v)) else v

        def get_factor(name):
            if cache_hit:
                return cache_hit.get(name)
            return None

        mom = get_factor("momentum") or (round(float(momentum_scores.get(ticker, 0)), 1) if ticker in momentum_scores.index and not pd.isna(momentum_scores.get(ticker)) else None)
        qua = get_factor("quality") or (round(float(quality_scores.get(ticker, 0)), 1) if ticker in quality_scores.index and not pd.isna(quality_scores.get(ticker)) else None)
        val = get_factor("value") or (round(float(value_scores.get(ticker, 0)), 1) if ticker in value_scores.index and not pd.isna(value_scores.get(ticker)) else None)
        gro = get_factor("growth") or (round(float(growth_scores.get(ticker, 0)), 1) if ticker in growth_scores.index and not pd.isna(growth_scores.get(ticker)) else None)
        comp = get_factor("composite") or (round(float(composite_scores.get(ticker, 0)), 1) if ticker in composite_scores.index and not pd.isna(composite_scores.get(ticker)) else None)

        change_pct = n(round(((price - prev_close) / prev_close) * 100, 2) if prev_close else 0)
        sector_val = fund.get("sector")
        if sector_val is None or (isinstance(sector_val, float) and pd.isna(sector_val)):
            sector_val = "Unknown"

        from services.seed_data import _STOCK_MAP
        s_data = _STOCK_MAP.get(ticker)
        name_val = fund.get("name") or (s_data[1] if s_data else ticker)

        result = ScreenerResult(
            ticker=ticker,
            name=name_val,
            sector=sector_val,
            price=price,
            change_pct=change_pct,
            pe_ratio=n(fund.get("pe_ratio")),
            pb_ratio=n(fund.get("pb_ratio")),
            roe=n(fund.get("roe")),
            revenue_growth=n(fund.get("revenue_growth")),
            momentum_score=mom,
            quality_score=qua,
            value_score=val,
            growth_score=gro,
            composite_score=comp,
            market_cap=n(fund.get("market_cap")),
        )
        results.append(result)

    filtered = results
    if filters.sector:
        filtered = [r for r in filtered if r.sector == filters.sector]
    if filters.min_pe is not None:
        filtered = [r for r in filtered if r.pe_ratio and r.pe_ratio >= filters.min_pe]
    if filters.max_pe is not None:
        filtered = [r for r in filtered if r.pe_ratio and r.pe_ratio <= filters.max_pe]
    if filters.min_roe is not None:
        filtered = [r for r in filtered if r.roe and r.roe >= filters.min_roe]
    if filters.min_momentum is not None:
        filtered = [r for r in filtered if r.momentum_score and r.momentum_score >= filters.min_momentum]
    if filters.min_quality is not None:
        filtered = [r for r in filtered if r.quality_score and r.quality_score >= filters.min_quality]
    if filters.min_composite is not None:
        filtered = [r for r in filtered if r.composite_score and r.composite_score >= filters.min_composite]

    reverse = filters.sort_dir == "desc"
    sort_field = filters.sort_by if hasattr(ScreenerResult, filters.sort_by) else "composite_score"
    filtered.sort(key=lambda r: getattr(r, sort_field) or 0, reverse=reverse)

    paginated = filtered[filters.offset: filters.offset + filters.limit]

    return ScreenerResponse(
        results=paginated,
        total=len(results),
        filtered=len(filtered),
    )


@router.get("/sectors")
async def get_sectors():
    """Get list of available sectors for filtering."""
    sectors = get_seed_sectors()
    return {"sectors": sectors}


@router.get("/factor-definitions")
async def get_factor_definitions():
    return {
        "momentum": {
            "description": "12-1 month price momentum (Jegadeesh & Titman 1993).",
            "high_score_means": "Strong recent price performance relative to universe",
        },
        "quality": {
            "description": "Composite of ROE, margins, leverage, earnings quality (Piotroski/Novy-Marx).",
            "high_score_means": "Strong, stable, well-capitalised business fundamentals",
        },
        "value": {
            "description": "Inverse-ranked valuation multiples: PE, PB, EV/EBITDA, FCF yield.",
            "high_score_means": "Trading cheap relative to fundamentals vs peers",
        },
        "growth": {
            "description": "Revenue growth, EPS growth, operating profit growth trends.",
            "high_score_means": "Strong topline and bottomline growth trajectory",
        },
        "low_volatility": {
            "description": "Inverse-ranked 60-day realised volatility (Ang et al. 2006).",
            "high_score_means": "Lower price volatility — better risk-adjusted returns",
        },
        "composite": {
            "description": "Weighted blend: 25% Momentum + 25% Quality + 20% Value + 20% Growth + 10% Low Vol.",
            "high_score_means": "Strong all-around quantitative profile",
        },
    }
