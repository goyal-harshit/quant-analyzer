"""
factor_scoring.py — shared factor computation + fast universe snapshots.

Used by the screener and Quant Lab so both rank stocks with the *same* 15-factor
methodology. `seed_snapshot` builds a network-free fundamentals/price/quote
snapshot (warm cache where available, deterministic seed otherwise) so broad
(500-name) universes can be scored in well under a second on free data sources.
"""
from __future__ import annotations

import pandas as pd

from services.factor_engine import FactorEngine

_engine = FactorEngine()

# Ordered registry of the 15 factors QuantAI computes. Keep this in sync with the
# Quant Lab / screener factor-definitions endpoints.
FACTOR_NAMES: list[str] = [
    "momentum", "value", "quality", "growth", "low_volatility", "size",
    "reversal", "profitability", "financial_health", "dividend", "liquidity",
    "beta", "earnings_quality", "trend", "composite",
]

# Numeric fundamentals columns coerced before scoring (None -> NaN).
_NUMERIC_COLS = (
    "pe_ratio", "pb_ratio", "ev_ebitda", "ps_ratio", "fcf_yield", "roe", "roa",
    "gross_margin", "ebitda_margin", "net_margin", "debt_equity",
    "interest_coverage", "current_ratio", "revenue_growth", "eps_growth",
    "operating_profit_growth", "accruals_ratio", "dividend_yield", "market_cap",
)


def coerce_numeric(fund_df: pd.DataFrame) -> pd.DataFrame:
    for c in _NUMERIC_COLS:
        if c in fund_df.columns:
            fund_df[c] = pd.to_numeric(fund_df[c], errors="coerce")
    return fund_df


def compute_factor_scores(fund_df: pd.DataFrame, price_matrix: pd.DataFrame | None) -> dict[str, pd.Series]:
    """Compute all 15 factor scores (0-100) for the given universe.

    Factors whose inputs are missing return an empty Series and are surfaced as
    ``None`` per ticker downstream — never an error.
    """
    have_prices = price_matrix is not None and not price_matrix.empty
    empty = pd.Series(dtype=float)

    momentum = _engine.compute_momentum_score(price_matrix) if have_prices else empty
    quality = _engine.compute_quality_score(fund_df)
    value = _engine.compute_value_score(fund_df)
    growth = _engine.compute_growth_score(fund_df)
    low_vol = _engine.compute_low_vol_score(price_matrix) if have_prices else empty
    size = _engine.compute_size_score(fund_df["market_cap"]) if "market_cap" in fund_df.columns else empty
    reversal = _engine.compute_reversal_score(price_matrix) if have_prices else empty
    profitability = _engine.compute_profitability_score(fund_df)
    fin_health = _engine.compute_financial_health_score(fund_df)
    dividend = _engine.compute_dividend_score(fund_df)
    liquidity = _engine.compute_liquidity_score(fund_df)
    beta = _engine.compute_beta_score(price_matrix) if have_prices else empty
    earnings_q = _engine.compute_earnings_quality_score(fund_df)
    trend = _engine.compute_trend_score(price_matrix) if have_prices else empty
    composite = _engine.compute_composite(momentum, quality, value, growth, low_vol)

    return {
        "momentum": momentum, "value": value, "quality": quality, "growth": growth,
        "low_volatility": low_vol, "size": size, "reversal": reversal,
        "profitability": profitability, "financial_health": fin_health,
        "dividend": dividend, "liquidity": liquidity, "beta": beta,
        "earnings_quality": earnings_q, "trend": trend, "composite": composite,
    }


def weighted_composite(scores: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
    """Blend selected factor scores with user weights (skips missing factors)."""
    frame = pd.DataFrame({k: scores[k] for k in weights if k in scores})
    if frame.empty:
        return pd.Series(dtype=float)
    total = 0.0
    acc = pd.Series(0.0, index=frame.index)
    for factor, w in weights.items():
        if factor in frame.columns:
            col = frame[factor]
            acc = acc.add(col.fillna(col.mean()) * w, fill_value=0.0)
            total += w
    if total <= 0:
        return pd.Series(dtype=float)
    return (acc / total).clip(0, 100)


def seed_snapshot(universe: list[str]) -> tuple[list[dict], dict, dict]:
    """Network-free fundamentals + price + quote snapshot for broad screening.

    Prefers live values already warm in the in-process caches; otherwise uses
    deterministic seed data. Issues no network calls.
    """
    from services.data_service import data_service, fundamentals_cache, quote_cache
    from services.seed_data import get_seed_fundamentals, get_seed_quote, get_seed_price_history

    key_map = data_service._SEED_KEY_MAP
    funds: list[dict] = []
    prices: dict = {}
    quotes: dict = {}
    for t in universe:
        cached = fundamentals_cache.get(f"fund_{t}")
        if isinstance(cached, dict) and (cached.get("pe_ratio") or cached.get("roe")):
            f = dict(cached)
        else:
            raw = get_seed_fundamentals(t) or {}
            f = {key_map.get(k, k): v for k, v in raw.items()}
            f["source"] = "seed"
        f["ticker"] = t
        if not f.get("sector"):
            f["sector"] = data_service._SECTOR_MAP.get(t)
        funds.append(f)

        hist = get_seed_price_history(t)
        if hist:
            prices[t] = pd.Series([h["close"] for h in hist])

        wq = quote_cache.get(f"quote_{t}")
        quotes[t] = wq if isinstance(wq, dict) and wq.get("price") else get_seed_quote(t)
    return funds, prices, quotes
