"""Sector analytics router — /api/v1/sectors"""

import logging

from fastapi import APIRouter, HTTPException

from . import service
from .schemas import SectorsResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/performance", response_model=SectorsResponse)
async def sector_performance(refresh: bool = False):
    """Sector tiles: avg change, advancers/decliners, top mover, avg P/E & ROE, components."""
    try:
        return await service.get_sectors(refresh=refresh)
    except Exception as e:
        logger.error(f"sector performance failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to compute sector performance")


@router.get("/heatmap")
async def sector_heatmap(refresh: bool = False):
    """Compact {sector: change_pct} map for heatmap rendering."""
    data = await service.get_sectors(refresh=refresh)
    return {"heatmap": data.heatmap, "sentiment": data.sentiment}


@router.get("/{sector}/stocks")
async def sector_stocks(sector: str, refresh: bool = False):
    """All universe stocks in a sector, ranked by composite score."""
    stocks = await service.get_sector_stocks(sector, refresh=refresh)
    if not stocks:
        raise HTTPException(status_code=404, detail=f"No stocks found for sector '{sector}'")
    return {"sector": sector, "count": len(stocks), "stocks": stocks}
