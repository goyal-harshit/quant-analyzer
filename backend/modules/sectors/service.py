"""
Sector analytics service — aggregate a broad NSE universe by sector.

Sector membership comes from SECTOR_UNIVERSE (~115 liquid names, deep enough
that every sector has several constituents — not the 1-2 you get from grouping
just the Nifty 50). The Nifty-50 core keeps its live composite/momentum scores
(reused from get_universe_overview); the extra names are filled with fast live
quotes, so the page is rich without paying for 115 composite computations.
"""

import json
import logging
from collections import defaultdict
from typing import List, Optional

from services.data_service import data_service, fundamentals_cache, _gather_limited, _get_redis
from services.fast_data import fast_data_service
from .schemas import ComponentStock, SectorPerf, Sentiment, SectorsResponse

logger = logging.getLogger(__name__)

_CACHE_KEY = "sectors_perf_v2"
_CACHE_TTL = 300  # 5 minutes

# Sector → constituents. Deliberately broad so each sector tile has depth.
SECTOR_UNIVERSE: dict[str, List[str]] = {
    "Financial Services": [
        "HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN", "INDUSINDBK",
        "BANKBARODA", "PNB", "FEDERALBNK", "IDFCFIRSTB", "BAJFINANCE", "BAJAJFINSV",
        "SHRIRAMFIN", "CHOLAFIN", "MUTHOOTFIN", "SBICARD", "PFC", "RECLTD",
        "HDFCLIFE", "SBILIFE", "ICICIPRULI", "HDFCAMC",
    ],
    "Technology": [
        "TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM", "PERSISTENT", "COFORGE", "MPHASIS",
    ],
    "Energy": [
        "RELIANCE", "ONGC", "NTPC", "POWERGRID", "COALINDIA", "IOC", "BPCL", "GAIL",
        "TATAPOWER", "ADANIGREEN",
    ],
    "Consumer Goods": [
        "HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "TATACONSUM", "DABUR", "MARICO",
        "GODREJCP", "COLPAL", "VBL", "UNITDSPR", "TITAN", "ASIANPAINT", "HAVELLS", "DMART", "TRENT",
    ],
    "Automobile": [
        "MARUTI", "TATAMOTORS", "M&M", "EICHERMOT", "BAJAJ-AUTO", "HEROMOTOCO", "TVSMOTOR",
        "ASHOKLEY", "BHARATFORG", "MOTHERSON",
    ],
    "Healthcare": [
        "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "APOLLOHOSP", "LUPIN", "AUROPHARMA",
        "BIOCON", "TORNTPHARM", "ZYDUSLIFE", "MAXHEALTH",
    ],
    "Metals & Mining": [
        "JSWSTEEL", "TATASTEEL", "HINDALCO", "VEDL", "NMDC", "SAIL", "JINDALSTEL", "HINDZINC",
    ],
    "Construction": [
        "LT", "ULTRACEMCO", "GRASIM", "SHREECEM", "AMBUJACEM", "ACC",
    ],
    "Realty": [
        "DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "PHOENIXLTD",
    ],
    "Telecommunications": [
        "BHARTIARTL", "IDEA", "INDUSTOWER", "TATACOMM",
    ],
    "Chemicals": [
        "UPL", "PIDILITIND", "SRF", "DEEPAKNTR", "AARTIIND", "NAVINFLUOR", "TATACHEM",
    ],
    "Infrastructure": [
        "ADANIPORTS", "ADANIENT", "GMRAIRPORT", "IRB", "IRCTC",
    ],
    "Media": [
        "ZEEL", "SUNTV", "PVRINOX",
    ],
}

# ticker -> sector (first wins)
TICKER_SECTOR: dict[str, str] = {t: sec for sec, lst in SECTOR_UNIVERSE.items() for t in lst}
ALL_TICKERS: List[str] = list(TICKER_SECTOR.keys())

MAX_COMPONENTS = 15


def _avg(vals: List[Optional[float]]) -> Optional[float]:
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def _component(s: dict) -> ComponentStock:
    return ComponentStock(
        ticker=s.get("ticker", ""),
        name=s.get("name", s.get("ticker", "")),
        price=round(float(s.get("price", 0) or 0), 2),
        change_pct=round(float(s.get("change_pct", 0) or 0), 2),
        composite_score=s.get("composite_score"),
    )


async def _build_rows(refresh: bool) -> List[dict]:
    """One row per universe stock: Nifty-50 core carries live composites; the rest
    are filled from fast quotes (composite/momentum left None)."""
    core = await data_service.get_universe_overview(refresh=refresh)
    by_ticker = {u.get("ticker"): u for u in core if u.get("ticker")}

    extra = [t for t in ALL_TICKERS if t not in by_ticker]

    # Fast-fail Yahoo-v8 quotes only — NOT data_service.get_quote, whose yfinance
    # backoff fallback turns a few unresolved tickers into a 90s stall.
    async def _fast_quote(t: str) -> Optional[dict]:
        try:
            q = await fast_data_service.get_quote(t)
            return q if q and q.get("price") else None
        except Exception:
            return None

    extra_quotes = {}
    if extra:
        results = await _gather_limited([_fast_quote(t) for t in extra], limit=12)
        extra_quotes = {t: q for t, q in zip(extra, results) if isinstance(q, dict)}

    rows: List[dict] = []
    for ticker in ALL_TICKERS:
        sector = TICKER_SECTOR[ticker]
        core_row = by_ticker.get(ticker)
        if core_row and core_row.get("price"):
            rows.append({**core_row, "sector": sector})
            continue
        q = extra_quotes.get(ticker)
        if q and not isinstance(q, Exception) and q.get("price"):
            rows.append({
                "ticker": ticker, "name": q.get("name", ticker), "sector": sector,
                "price": q.get("price", 0.0), "change_pct": q.get("change_pct", 0.0),
                "composite_score": None, "momentum_score": None,
            })
    return rows


async def get_sectors(refresh: bool = False) -> SectorsResponse:
    if not refresh:
        try:
            r = await _get_redis()
            if r:
                cached = await r.get(_CACHE_KEY)
                if cached:
                    return SectorsResponse(**json.loads(cached))
        except Exception:
            pass

    rows = await _build_rows(refresh)

    groups: dict[str, List[dict]] = defaultdict(list)
    for r in rows:
        groups[r["sector"]].append(r)

    sectors: List[SectorPerf] = []
    for name in SECTOR_UNIVERSE:  # stable, intended order before re-sort
        stocks = groups.get(name, [])
        if not stocks:
            continue
        changes = [s.get("change_pct") for s in stocks if s.get("change_pct") is not None]
        pes = [fundamentals_cache.get(f"fund_{s['ticker']}", {}).get("pe_ratio") for s in stocks]
        pes = [p for p in pes if isinstance(p, (int, float)) and p > 0]
        roes = [fundamentals_cache.get(f"fund_{s['ticker']}", {}).get("roe") for s in stocks]
        roes = [r for r in roes if isinstance(r, (int, float))]

        ranked = sorted(stocks, key=lambda s: s.get("change_pct", 0) or 0, reverse=True)
        sectors.append(SectorPerf(
            name=name,
            change_pct=round(sum(changes) / len(changes), 2) if changes else 0.0,
            week_pct=None, month_pct=None,
            avg_pe=_avg(pes),
            avg_roe=_avg(roes),
            momentum_score=_avg([s.get("momentum_score") for s in stocks]),
            composite_score=_avg([s.get("composite_score") for s in stocks]),
            stock_count=len(stocks),
            advancers=sum(1 for c in changes if c > 0),
            decliners=sum(1 for c in changes if c < 0),
            top_gainer=_component(ranked[0]) if ranked else None,
            top_loser=_component(ranked[-1]) if ranked else None,
            components=[_component(s) for s in ranked[:MAX_COMPONENTS]],
        ))

    sectors.sort(key=lambda s: s.change_pct, reverse=True)

    heatmap = {s.name: s.change_pct for s in sectors}
    sentiment = Sentiment(
        bullish=sum(1 for s in sectors if s.change_pct > 0.1),
        bearish=sum(1 for s in sectors if s.change_pct < -0.1),
        neutral=sum(1 for s in sectors if -0.1 <= s.change_pct <= 0.1),
    )

    all_sorted = sorted(rows, key=lambda s: s.get("change_pct", 0) or 0, reverse=True)
    top_gainers = [_component(s) for s in all_sorted[:5]]
    top_losers = [_component(s) for s in all_sorted[-5:]][::-1]

    resp = SectorsResponse(
        sectors=sectors, heatmap=heatmap, sentiment=sentiment,
        top_gainers=top_gainers, top_losers=top_losers,
    )
    try:
        r = await _get_redis()
        if r:
            await r.setex(_CACHE_KEY, _CACHE_TTL, resp.model_dump_json())
    except Exception:
        pass
    return resp


async def get_sector_stocks(sector: str, refresh: bool = False) -> List[ComponentStock]:
    rows = await _build_rows(refresh)
    target = sector.strip().lower()
    matches = [r for r in rows if r["sector"].lower() == target]
    matches.sort(key=lambda s: s.get("change_pct", 0) or 0, reverse=True)
    return [_component(s) for s in matches]
