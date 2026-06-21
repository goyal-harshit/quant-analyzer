"""
Comparison service — gather metrics for 2-5 assets and rank them.

Per asset: live quote + fundamentals + 1y price history, then the shared
compute_quant_factors() engine for 0-100 factor scores. Price-derived stats
(period return, annualised volatility, Sharpe, max drawdown) are computed here.
"""

import logging
from typing import List, Optional

import numpy as np

from services.data_service import data_service, _gather_limited
from services.fast_data import compute_quant_factors
from .schemas import (
    AssetComparison, FactorScores, BestPick, CompareResponse,
)

logger = logging.getLogger(__name__)

RISK_FREE = 0.06  # ~Indian 10y; used for Sharpe


def _price_stats(close: np.ndarray) -> dict:
    """Period return, annualised volatility, Sharpe, max drawdown from a close series."""
    out = {"returns_period": None, "volatility": None, "sharpe_ratio": None, "max_drawdown": None}
    if close is None or len(close) < 2:
        return out
    out["returns_period"] = round(float((close[-1] / close[0] - 1) * 100), 2)
    daily = np.diff(close) / close[:-1]
    daily = daily[np.isfinite(daily)]
    if len(daily) >= 2:
        vol = float(np.std(daily) * np.sqrt(252))
        out["volatility"] = round(vol * 100, 2)
        ann_ret = float(np.mean(daily) * 252)
        out["sharpe_ratio"] = round((ann_ret - RISK_FREE) / vol, 2) if vol > 0 else 0.0
    cummax = np.maximum.accumulate(close)
    dd = (close - cummax) / cummax
    out["max_drawdown"] = round(float(np.min(dd) * 100), 2)
    return out


async def _gather_asset(ticker: str, period: str) -> Optional[AssetComparison]:
    ticker = ticker.upper().strip()
    try:
        quote = await data_service.get_quote(ticker)
        if not quote or not quote.get("price"):
            return None
        fundamentals = await data_service.get_fundamentals(ticker)
        df = await data_service.get_price_history(ticker, period=period)

        close_arr = None
        factors = {}
        spark: List[float] = []
        if df is not None and not getattr(df, "empty", True):
            d2 = df.copy()
            d2.columns = [str(c).lower() for c in d2.columns]
            if "close" in d2.columns:
                close_series = d2["close"].dropna()
                close_arr = close_series.to_numpy(dtype=float)
                factors = compute_quant_factors(d2, fundamentals or {})
                # ~40-point sparkline
                vals = close_series.tolist()
                step = max(1, len(vals) // 40)
                spark = [round(float(v), 2) for v in vals[::step]]

        stats = _price_stats(close_arr)

        # Low-volatility score (0-100): lower annualised vol → higher score.
        low_vol = None
        if stats["volatility"] is not None:
            low_vol = round(max(0.0, min(100.0, 100.0 - stats["volatility"] * 1.5)), 1)

        return AssetComparison(
            ticker=ticker,
            name=quote.get("name", ticker),
            sector=(fundamentals or {}).get("sector"),
            price=round(float(quote["price"]), 2),
            change_pct=round(float(quote.get("change_pct", 0.0) or 0.0), 2),
            pe_ratio=(fundamentals or {}).get("pe_ratio"),
            pb_ratio=(fundamentals or {}).get("pb_ratio"),
            roe=(fundamentals or {}).get("roe"),
            dividend_yield=(fundamentals or {}).get("dividend_yield"),
            debt_equity=(fundamentals or {}).get("debt_equity"),
            market_cap=(fundamentals or {}).get("market_cap"),
            returns_period=stats["returns_period"],
            volatility=stats["volatility"],
            sharpe_ratio=stats["sharpe_ratio"],
            max_drawdown=stats["max_drawdown"],
            scores=FactorScores(
                momentum=factors.get("momentum_score"),
                quality=factors.get("quality_score"),
                value=factors.get("value_score"),
                growth=factors.get("growth_score"),
                low_vol=low_vol,
                composite=factors.get("composite_score"),
            ),
            spark=spark,
            source=(fundamentals or {}).get("source", "live"),
        )
    except Exception as e:
        logger.warning(f"compare: failed to gather {ticker}: {e}")
        return None


def _best(assets: List[AssetComparison], key, higher_better: bool, label_fmt) -> BestPick:
    """Pick the best asset by a (possibly-None) metric accessor."""
    candidates = [(a, key(a)) for a in assets if key(a) is not None]
    if not candidates:
        return BestPick(reason="Not enough data")
    winner, value = (max if higher_better else min)(candidates, key=lambda x: x[1])
    return BestPick(ticker=winner.ticker, value=round(float(value), 2), reason=label_fmt(winner, value))


async def compare_stocks(tickers: List[str], period: str = "1y") -> CompareResponse:
    uniq = list(dict.fromkeys(t.upper().strip() for t in tickers if t.strip()))
    results = await _gather_limited([_gather_asset(t, period) for t in uniq], limit=5)
    assets = [a for a in results if isinstance(a, AssetComparison)]
    if len(assets) < 2:
        raise ValueError("Could not fetch data for at least 2 of the requested tickers")

    # Radar matrix (0-100 factor scores per asset).
    radar_metrics = [
        ("Momentum", lambda a: a.scores.momentum),
        ("Quality", lambda a: a.scores.quality),
        ("Value", lambda a: a.scores.value),
        ("Growth", lambda a: a.scores.growth),
        ("Low Vol", lambda a: a.scores.low_vol),
        ("Composite", lambda a: a.scores.composite),
    ]
    radar = []
    for label, accessor in radar_metrics:
        row: dict = {"metric": label}
        for a in assets:
            v = accessor(a)
            row[a.ticker] = round(float(v), 1) if v is not None else 0.0
        radar.append(row)

    best_momentum = _best(assets, lambda a: a.scores.momentum, True,
                          lambda a, v: f"{a.name} leads on momentum ({v:.0f}/100)")
    best_quality = _best(assets, lambda a: a.scores.quality, True,
                        lambda a, v: f"{a.name} has the strongest quality profile ({v:.0f}/100)")
    best_value = _best(assets, lambda a: a.scores.value, True,
                      lambda a, v: f"{a.name} screens cheapest on valuation ({v:.0f}/100)")
    best_risk_adjusted = _best(assets, lambda a: a.sharpe_ratio, True,
                              lambda a, v: f"{a.name} has the best risk-adjusted return (Sharpe {v:.2f})")
    best_return = _best(assets, lambda a: a.returns_period, True,
                       lambda a, v: f"{a.name} delivered the highest return ({v:+.1f}%)")

    # Rule-based recommendation from the composite score.
    comp = [(a, a.scores.composite) for a in assets if a.scores.composite is not None]
    if comp:
        top, top_score = max(comp, key=lambda x: x[1])
        recommendation = (
            f"On a blended factor basis, {top.name} ({top.ticker}) ranks highest "
            f"(composite {top_score:.0f}/100)"
        )
        extras = []
        if best_value.ticker and best_value.ticker != top.ticker:
            extras.append(f"{best_value.ticker} screens as the better value pick")
        if best_momentum.ticker and best_momentum.ticker != top.ticker:
            extras.append(f"{best_momentum.ticker} has stronger momentum")
        if extras:
            recommendation += " — " + "; ".join(extras)
        recommendation += "."
    else:
        recommendation = "Insufficient factor data to rank these assets confidently."

    return CompareResponse(
        assets=assets,
        radar=radar,
        best_momentum=best_momentum,
        best_quality=best_quality,
        best_value=best_value,
        best_risk_adjusted=best_risk_adjusted,
        best_return=best_return,
        recommendation=recommendation,
    )
