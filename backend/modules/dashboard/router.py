"""Dashboard Router — Market overview and watchlist performance"""

from fastapi import APIRouter
from services.data_service import data_service

router = APIRouter()


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
