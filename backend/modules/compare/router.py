"""Comparison router — /api/v1/compare"""

import logging

from fastapi import APIRouter, HTTPException, Query

from . import service
from .schemas import CompareRequest, CompareResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/stocks", response_model=CompareResponse)
async def compare_stocks(req: CompareRequest):
    """Compare 2-5 stocks: fundamentals, returns/risk, factor radar, best-in-class picks."""
    if not 2 <= len(req.tickers) <= 5:
        raise HTTPException(status_code=400, detail="Compare between 2 and 5 tickers")
    try:
        return await service.compare_stocks(req.tickers, req.period)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"compare failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Comparison failed")


@router.get("/stocks", response_model=CompareResponse)
async def compare_stocks_get(
    tickers: str = Query(..., description="Comma-separated tickers, e.g. INFY,TCS,HCLTECH"),
    period: str = Query("1y"),
):
    """Convenience GET form: /compare/stocks?tickers=INFY,TCS,HCLTECH"""
    parts = [t.strip() for t in tickers.split(",") if t.strip()]
    if not 2 <= len(parts) <= 5:
        raise HTTPException(status_code=400, detail="Compare between 2 and 5 tickers")
    try:
        return await service.compare_stocks(parts, period)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"compare failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Comparison failed")
