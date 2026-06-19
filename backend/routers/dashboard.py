"""Dashboard Router — Market overview and watchlist performance"""

from fastapi import APIRouter
from services.data_service import data_service
from services.seed_data import get_universe_overview, get_sector_performance, get_market_indices

router = APIRouter()


@router.get("/market-summary")
async def get_market_summary():
    """Get market indices summary for dashboard."""
    return await data_service.get_market_summary()


@router.get("/top-gainers-losers")
async def get_top_movers():
    """Get top gainers and losers from the universe."""
    universe = get_universe_overview()
    sorted_by_chg = sorted(universe, key=lambda x: x["change_pct"], reverse=True)
    return {
        "gainers": sorted_by_chg[:5],
        "losers": sorted_by_chg[-5:],
    }


@router.get("/sector-performance")
async def get_sector_perf():
    """Get sector performance for dashboard."""
    return await data_service.get_sector_performance()


@router.get("/factor-signals")
async def get_factor_signals():
    """Get top factor signals (composite scores) for dashboard."""
    universe = get_universe_overview()
    return {
        "signals": sorted(universe, key=lambda x: x.get("change_pct", 0), reverse=True)[:10],
    }


@router.get("/universe-overview")
async def get_universe():
    """Get overview of all stocks in the universe."""
    return get_universe_overview()
