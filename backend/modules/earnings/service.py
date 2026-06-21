"""
Earnings service — real quarterly figures sourced from screener.in (via the
shared data_service fundamentals, which scrapes the latest quarter). No hardcoded
data; returns what the live source provides.
"""

from __future__ import annotations

import logging

from services.data_service import data_service, NIFTY_50_TICKERS, _gather_limited

logger = logging.getLogger(__name__)


async def get_ticker_earnings(ticker: str) -> dict:
    t = ticker.upper()
    f = await data_service.get_fundamentals(t)
    rev = f.get("quarterly_revenue_cr") or f.get("revenue_cr")
    profit = f.get("quarterly_net_profit_cr") or f.get("net_profit_cr")
    eps = f.get("quarterly_eps") or f.get("eps")
    margin = round((profit / rev) * 100, 2) if (rev and profit) else None
    has = any(v is not None for v in (rev, profit, eps))
    return {
        "ticker": t,
        "name": f.get("name") or t,
        "history": [
            {
                "period": "Latest quarter",
                "revenue_cr": rev,
                "net_profit_cr": profit,
                "eps": eps,
                "net_margin_pct": margin,
            }
        ] if has else [],
        "source": "screener.in" if has else "unavailable",
    }


async def get_calendar(limit: int = 15) -> dict:
    """Recently-reported results across the liquid universe (proxy for an
    earnings calendar — NSE/BSE don't expose a free upcoming-earnings feed)."""
    results = await _gather_limited(
        [data_service.get_fundamentals(t) for t in NIFTY_50_TICKERS[:limit]], limit=4
    )
    rows = []
    for t, f in zip(NIFTY_50_TICKERS[:limit], results):
        if not isinstance(f, dict):
            continue
        rev = f.get("quarterly_revenue_cr") or f.get("revenue_cr")
        profit = f.get("quarterly_net_profit_cr") or f.get("net_profit_cr")
        if rev or profit:
            rows.append({
                "ticker": t,
                "name": f.get("name") or t,
                "revenue_cr": rev,
                "net_profit_cr": profit,
                "eps": f.get("quarterly_eps") or f.get("eps"),
            })
    return {"recent": rows, "count": len(rows), "source": "screener.in"}
