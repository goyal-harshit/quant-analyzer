"""Dashboard Router — Market overview and watchlist performance"""

from fastapi import APIRouter, HTTPException, Query
from services.data_service import data_service, NIFTY_50_TICKERS, _gather_limited

router = APIRouter()

# ── Index registry: all live NSE/BSE indices (Yahoo symbols verified) ──────
# `sector` maps a sectoral index to its constituents (from the sectors universe);
# `constituents` is a named source for broad indices.
INDICES = [
    {"name": "NIFTY 50", "symbol": "^NSEI", "group": "Broad", "constituents": "nifty50"},
    {"name": "SENSEX", "symbol": "^BSESN", "group": "Broad", "constituents": "nifty50"},
    {"name": "NIFTY NEXT 50", "symbol": "^NSMIDCP", "group": "Broad", "constituents": "universe"},
    {"name": "NIFTY 500", "symbol": "^CRSLDX", "group": "Broad", "constituents": "universe"},
    {"name": "NIFTY MIDCAP 50", "symbol": "^NSEMDCP50", "group": "Broad", "constituents": "universe"},
    {"name": "BANK NIFTY", "symbol": "^NSEBANK", "group": "Sectoral", "sector": "Financial Services"},
    {"name": "NIFTY FIN SERVICE", "symbol": "NIFTY_FIN_SERVICE.NS", "group": "Sectoral", "sector": "Financial Services"},
    {"name": "NIFTY IT", "symbol": "^CNXIT", "group": "Sectoral", "sector": "Technology"},
    {"name": "NIFTY AUTO", "symbol": "^CNXAUTO", "group": "Sectoral", "sector": "Automobile"},
    {"name": "NIFTY PHARMA", "symbol": "^CNXPHARMA", "group": "Sectoral", "sector": "Healthcare"},
    {"name": "NIFTY FMCG", "symbol": "^CNXFMCG", "group": "Sectoral", "sector": "Consumer Goods"},
    {"name": "NIFTY METAL", "symbol": "^CNXMETAL", "group": "Sectoral", "sector": "Metals & Mining"},
    {"name": "NIFTY REALTY", "symbol": "^CNXREALTY", "group": "Sectoral", "sector": "Realty"},
    {"name": "NIFTY ENERGY", "symbol": "^CNXENERGY", "group": "Sectoral", "sector": "Energy"},
    {"name": "NIFTY INFRA", "symbol": "^CNXINFRA", "group": "Sectoral", "sector": "Infrastructure"},
    {"name": "NIFTY MEDIA", "symbol": "^CNXMEDIA", "group": "Sectoral", "sector": "Media"},
    {"name": "NIFTY PSU BANK", "symbol": "^CNXPSUBANK", "group": "Sectoral", "sector": "Financial Services"},
    {"name": "NIFTY PSE", "symbol": "^CNXPSE", "group": "Thematic", "constituents": "universe"},
    {"name": "INDIA VIX", "symbol": "^INDIAVIX", "group": "Volatility", "constituents": None},
]
_INDEX_BY_SYMBOL = {i["symbol"]: i for i in INDICES}


def _constituent_tickers(meta: dict) -> list[str]:
    """Resolve an index's constituent tickers from the sectors universe."""
    from modules.sectors.service import SECTOR_UNIVERSE, ALL_TICKERS
    if meta.get("sector"):
        return SECTOR_UNIVERSE.get(meta["sector"], [])
    src = meta.get("constituents")
    if src == "nifty50":
        return list(NIFTY_50_TICKERS)
    if src == "universe":
        return list(ALL_TICKERS)
    return []


@router.get("/market-summary")
async def get_market_summary(refresh: bool = False):
    """Get market indices summary for dashboard."""
    return await data_service.get_market_summary(refresh=refresh)


@router.get("/top-gainers-losers")
async def get_top_movers(refresh: bool = False):
    """Get top gainers and losers from the universe."""
    universe = await data_service.get_universe_overview(refresh=refresh)
    sorted_by_chg = sorted(universe, key=lambda x: x.get("change_pct", 0.0), reverse=True)
    return {
        "gainers": sorted_by_chg[:5],
        "losers": sorted_by_chg[-5:],
        "source": "live",
    }


@router.get("/sector-performance")
async def get_sector_perf(refresh: bool = False):
    """Get sector performance for dashboard."""
    return await data_service.get_sector_performance(refresh=refresh)


@router.get("/factor-signals")
async def get_factor_signals(refresh: bool = False):
    """Get top factor signals (composite scores) for dashboard."""
    universe = await data_service.get_universe_overview(refresh=refresh)
    return {
        "signals": sorted(universe, key=lambda x: x.get("composite_score", 0.0) or 0.0, reverse=True)[:10],
        "source": "live",
    }


@router.get("/universe-overview")
async def get_universe(refresh: bool = False):
    """Get overview of all stocks in the universe."""
    return await data_service.get_universe_overview(refresh=refresh)


@router.get("/indices")
async def get_all_indices(refresh: bool = False):
    """Live quotes for ALL tracked NSE/BSE indices (broad, sectoral, thematic)."""
    quotes = await _gather_limited(
        [data_service.get_quote(i["symbol"], refresh=refresh) for i in INDICES], limit=10
    )
    out = []
    for meta, q in zip(INDICES, quotes):
        if q and not isinstance(q, Exception) and q.get("price"):
            out.append({
                "name": meta["name"], "symbol": meta["symbol"], "group": meta["group"],
                "last": round(q["price"], 2),
                "change": round(q.get("change", 0.0) or 0.0, 2),
                "change_pct": round(q.get("change_pct", 0.0) or 0.0, 2),
                "as_of": q.get("as_of"),
            })
    return {"indices": out}


@router.get("/index")
async def get_index_detail(symbol: str = Query(...), refresh: bool = False):
    """One index: live quote + its constituent stocks (sorted by day change)."""
    meta = _INDEX_BY_SYMBOL.get(symbol)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Unknown index {symbol}")

    q = await data_service.get_quote(symbol, refresh=refresh) or {}
    tickers = _constituent_tickers(meta)
    constituents = []
    if tickers:
        cq = await data_service.get_batch_quotes(tickers, refresh=refresh)
        for t in tickers:
            qq = cq.get(t)
            if qq and not isinstance(qq, Exception) and qq.get("price"):
                constituents.append({
                    "ticker": t,
                    "name": qq.get("name", t),
                    "price": round(qq.get("price", 0.0), 2),
                    "change_pct": round(qq.get("change_pct", 0.0) or 0.0, 2),
                    "sector": data_service._SECTOR_MAP.get(t, "Diversified"),
                })
        constituents.sort(key=lambda x: x["change_pct"], reverse=True)

    advancers = sum(1 for c in constituents if c["change_pct"] > 0)
    decliners = sum(1 for c in constituents if c["change_pct"] < 0)
    return {
        "name": meta["name"], "symbol": symbol, "group": meta["group"],
        "last": round(q.get("price", 0.0), 2),
        "change": round(q.get("change", 0.0) or 0.0, 2),
        "change_pct": round(q.get("change_pct", 0.0) or 0.0, 2),
        "as_of": q.get("as_of"),
        "advancers": advancers, "decliners": decliners,
        "constituents": constituents,
    }
