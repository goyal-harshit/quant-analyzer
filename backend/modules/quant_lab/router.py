"""Quant Lab Router — custom multi-factor model builder (15 factors)."""

from fastapi import APIRouter, HTTPException
import numpy as np
import pandas as pd

from services.data_service import data_service, _gather_limited
from services.universe import NIFTY_500_TICKERS
from services.factor_engine import FactorEngine, PortfolioAnalytics
from services.factor_scoring import (
    FACTOR_NAMES,
    coerce_numeric,
    compute_factor_scores,
    seed_snapshot,
    weighted_composite,
)
from models.schemas import FactorModelRequest

router = APIRouter()
engine = FactorEngine()

# Universes too large to fan out live on free data sources — use the fast
# network-free snapshot (warm cache + deterministic seed) instead.
_BROAD_UNIVERSES = {"NIFTY200", "NIFTY500", "BSE500"}


def _to_frame(fund_list: list[dict], price_map: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    fund_df = coerce_numeric(pd.DataFrame(fund_list).set_index("ticker"))
    price_matrix = pd.DataFrame(price_map) if price_map else pd.DataFrame()
    return fund_df, price_matrix


async def _load_universe(request: FactorModelRequest) -> tuple[list[dict], dict, dict]:
    """Resolve the request universe to (fundamentals, price_map, quote_map)."""
    if request.tickers and len(request.tickers) > 0:
        universe = request.tickers
        broad = len(universe) > 80
    else:
        u = (getattr(request, "universe", None) or "NIFTY500").upper()
        if u == "NIFTY50":
            from services.data_service import NIFTY_50_TICKERS
            universe = list(NIFTY_50_TICKERS)
            broad = False
        else:
            universe = list(NIFTY_500_TICKERS)
            broad = True

    if broad:
        return seed_snapshot(universe)

    # Small / custom universe → live fetch.
    _all = await _gather_limited(
        [
            *[data_service.get_fundamentals(t) for t in universe],
            *[data_service.get_price_history(t, period="1y") for t in universe],
        ],
        limit=12,
    )
    n = len(universe)
    funds, hists = _all[:n], _all[n:]
    fund_list = []
    for ticker, fund in zip(universe, funds):
        if isinstance(fund, dict) and fund:
            f = dict(fund)
            f["ticker"] = ticker
            if not f.get("sector"):
                f["sector"] = data_service._SECTOR_MAP.get(ticker)
            fund_list.append(f)
    price_map = {}
    for ticker, df in zip(universe, hists):
        if isinstance(df, pd.DataFrame) and not df.empty:
            price_map[ticker] = df["close"].reset_index(drop=True)
    return fund_list, price_map, {}


def _safe(v):
    if v is None:
        return None
    if isinstance(v, float) and (pd.isna(v) or np.isinf(v)):
        return None
    return round(float(v), 1)


@router.post("/score")
async def score_universe(request: FactorModelRequest):
    """
    Score a universe using a custom 15-factor model.
    Returns ranked results with a user-weighted composite plus every individual
    factor score.
    """
    fund_list, price_map, _quotes = await _load_universe(request)
    if not fund_list:
        raise HTTPException(status_code=503, detail="Unable to fetch universe data")

    fund_df, price_matrix = _to_frame(fund_list, price_map)
    scores = compute_factor_scores(fund_df, price_matrix)

    # User weights override the default composite; fall back to the engine's
    # 5-factor composite when no weights are supplied.
    weights = {k: float(v) for k, v in (request.factor_weights or {}).items() if v}
    composite = weighted_composite(scores, weights) if weights else scores["composite"]

    results = []
    for ticker in fund_df.index:
        row = {"ticker": ticker, "sector": fund_df.loc[ticker].get("sector")}
        for name in FACTOR_NAMES:
            if name == "composite":
                continue
            series = scores.get(name)
            row[name] = _safe(series.get(ticker)) if series is not None and ticker in series.index else None
        row["composite"] = _safe(composite.get(ticker)) if ticker in composite.index else None
        results.append(row)

    results.sort(key=lambda x: x["composite"] if x["composite"] is not None else -1, reverse=True)
    return {
        "model_name": request.name,
        "factors": FACTOR_NAMES,
        "weights": weights or engine_default_weights(),
        "count": len(results),
        "results": results,
    }


def engine_default_weights() -> dict:
    from services.factor_engine import DEFAULT_WEIGHTS
    return dict(DEFAULT_WEIGHTS)


@router.post("/optimize")
async def optimize_portfolio(request: FactorModelRequest):
    """
    Build a long-only factor-tilted portfolio from the top-ranked names and
    report its historical risk/return (equal-weight vs score-weighted).
    """
    fund_list, price_map, _quotes = await _load_universe(request)
    if not fund_list:
        raise HTTPException(status_code=503, detail="Unable to fetch universe data")

    fund_df, price_matrix = _to_frame(fund_list, price_map)
    scores = compute_factor_scores(fund_df, price_matrix)
    weights = {k: float(v) for k, v in (request.factor_weights or {}).items() if v}
    composite = weighted_composite(scores, weights) if weights else scores["composite"]

    top_n = min(20, max(5, len(composite) // 5))
    top = composite.dropna().sort_values(ascending=False).head(top_n)
    if top.empty or price_matrix.empty:
        raise HTTPException(status_code=422, detail="Not enough data to optimise")

    members = [t for t in top.index if t in price_matrix.columns]
    if not members:
        raise HTTPException(status_code=422, detail="No price history for selected names")

    # Score-weighted allocation (normalised).
    w = top.loc[members]
    w = w / w.sum()

    rets = price_matrix[members].pct_change().dropna()
    port_rets = (rets * w.values).sum(axis=1)
    equity = (1 + port_rets).cumprod()

    pa = PortfolioAnalytics
    holdings = [
        {"ticker": t, "weight": round(float(w[t]) * 100, 2),
         "composite": _safe(composite.get(t)),
         "sector": fund_df.loc[t].get("sector") if t in fund_df.index else None}
        for t in members
    ]
    return {
        "model_name": request.name,
        "holdings": sorted(holdings, key=lambda x: x["weight"], reverse=True),
        "metrics": {
            "annual_return_pct": round(float(port_rets.mean() * 252 * 100), 2),
            "annual_volatility_pct": round(float(port_rets.std() * np.sqrt(252) * 100), 2),
            "sharpe": round(pa.sharpe_ratio(port_rets), 2),
            "sortino": round(pa.sortino_ratio(port_rets), 2),
            "max_drawdown_pct": round(pa.max_drawdown(equity) * 100, 2),
        },
    }


@router.post("/monte-carlo")
async def monte_carlo(request: FactorModelRequest, simulations: int = 500, horizon_days: int = 252):
    """
    Monte-Carlo projection of a factor-tilted portfolio's 1-year value using a
    bootstrap of historical daily returns.
    """
    simulations = max(100, min(2000, simulations))
    horizon_days = max(21, min(504, horizon_days))

    fund_list, price_map, _q = await _load_universe(request)
    if not fund_list:
        raise HTTPException(status_code=503, detail="Unable to fetch universe data")
    fund_df, price_matrix = _to_frame(fund_list, price_map)
    if price_matrix.empty:
        raise HTTPException(status_code=422, detail="No price history for simulation")

    scores = compute_factor_scores(fund_df, price_matrix)
    weights = {k: float(v) for k, v in (request.factor_weights or {}).items() if v}
    composite = weighted_composite(scores, weights) if weights else scores["composite"]

    top_n = min(20, max(5, len(composite) // 5))
    top = composite.dropna().sort_values(ascending=False).head(top_n)
    members = [t for t in top.index if t in price_matrix.columns]
    if not members:
        raise HTTPException(status_code=422, detail="No price history for selected names")

    w = top.loc[members]
    w = w / w.sum()
    port_rets = (price_matrix[members].pct_change().dropna() * w.values).sum(axis=1)
    if len(port_rets) < 30:
        raise HTTPException(status_code=422, detail="Insufficient return history")

    sample = port_rets.to_numpy()
    rng = np.random.default_rng(42)
    draws = rng.choice(sample, size=(simulations, horizon_days), replace=True)
    terminal = (1.0 + draws).prod(axis=1)

    pct = lambda p: round(float(np.percentile(terminal, p) - 1) * 100, 2)
    return {
        "model_name": request.name,
        "simulations": simulations,
        "horizon_days": horizon_days,
        "start_value": 100.0,
        "projected_return_pct": {
            "p5": pct(5), "p25": pct(25), "p50": pct(50), "p75": pct(75), "p95": pct(95),
        },
        "prob_loss_pct": round(float((terminal < 1).mean()) * 100, 2),
        "expected_value": round(float(np.mean(terminal) * 100), 2),
    }


@router.get("/factor-definitions")
async def get_factor_definitions():
    """Definitions of all 15 factors for the Quant Lab UI."""
    return {
        "momentum": {
            "label": "Momentum",
            "description": "12-1 month price momentum (Jegadeesh & Titman 1993). Relative price strength over the past year, skipping the most recent month.",
            "family": "Price",
        },
        "value": {
            "label": "Value",
            "description": "Inverse-ranked valuation multiples: PE, PB, EV/EBITDA, P/S, FCF yield (Fama-French value factor).",
            "family": "Valuation",
        },
        "quality": {
            "label": "Quality",
            "description": "ROE, gross/EBITDA margins, leverage and interest coverage (Piotroski / Novy-Marx).",
            "family": "Fundamental",
        },
        "growth": {
            "label": "Growth",
            "description": "Revenue growth, EPS growth and operating-profit growth trends.",
            "family": "Fundamental",
        },
        "low_volatility": {
            "label": "Low Volatility",
            "description": "Inverse-ranked 60-day realised volatility (low-vol anomaly, Ang et al. 2006).",
            "family": "Risk",
        },
        "size": {
            "label": "Size",
            "description": "Small-cap tilt (Fama-French 1993). Lower market cap scores higher.",
            "family": "Risk",
        },
        "reversal": {
            "label": "Short-Term Reversal",
            "description": "Contrarian 1-month reversal (Jegadeesh 1990). Recent losers score higher.",
            "family": "Price",
        },
        "profitability": {
            "label": "Profitability",
            "description": "Return on capital & margins (ROE, ROA, gross/net margin) — Novy-Marx gross profitability.",
            "family": "Fundamental",
        },
        "financial_health": {
            "label": "Financial Health",
            "description": "Balance-sheet strength: low debt/equity, high interest coverage and current ratio.",
            "family": "Fundamental",
        },
        "dividend": {
            "label": "Dividend Yield",
            "description": "Trailing dividend yield rank — income / shareholder-return tilt.",
            "family": "Valuation",
        },
        "liquidity": {
            "label": "Liquidity",
            "description": "Tradability proxy (inverse Amihud illiquidity) via log market cap.",
            "family": "Risk",
        },
        "beta": {
            "label": "Low Beta",
            "description": "Betting-against-beta (Frazzini-Pedersen 2014). Beta vs the equal-weight universe; low beta scores higher.",
            "family": "Risk",
        },
        "earnings_quality": {
            "label": "Earnings Quality",
            "description": "Low accruals (Sloan 1996) where available, else the Piotroski F-Score.",
            "family": "Fundamental",
        },
        "trend": {
            "label": "Trend",
            "description": "Distance of price above its 200-day moving average — trend-following signal.",
            "family": "Price",
        },
        "composite": {
            "label": "Composite",
            "description": "User-weighted blend of the factors above (defaults to 25/25/20/20/10 momentum/quality/value/growth/low-vol).",
            "family": "Blend",
        },
    }
