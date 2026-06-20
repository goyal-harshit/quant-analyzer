"""Mutual Funds router — /api/v1/mf"""

import logging

from fastapi import APIRouter, HTTPException, Query

from . import service
from .schemas import SIPRequest, CompareRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/search")
async def search(q: str = Query(..., min_length=2, description="Scheme/fund-house name")):
    """Search mutual fund schemes by name (mfapi.in, 14k+ schemes)."""
    results = await service.search_schemes(q)
    return {"query": q, "count": len(results), "results": results}


@router.get("/popular")
async def popular():
    """A small curated list of popular schemes for the empty state."""
    return {"results": service.SEED_SCHEMES}


@router.post("/sip-calculator")
async def sip_calculator(req: SIPRequest):
    """Project a monthly SIP's future value (with optional annual step-up)."""
    if req.monthly_amount <= 0 or req.years <= 0:
        raise HTTPException(status_code=400, detail="monthly_amount and years must be positive")
    return service.sip_projection(req.monthly_amount, req.years, req.expected_return, req.annual_step_up)


@router.post("/compare")
async def compare(req: CompareRequest):
    """Side-by-side returns + risk for 2-4 schemes."""
    if not 2 <= len(req.scheme_codes) <= 4:
        raise HTTPException(status_code=400, detail="Provide between 2 and 4 scheme_codes")
    return {"schemes": await service.compare(req.scheme_codes)}


@router.get("/{code}")
async def get_scheme(code: int, period: str = Query("3y", description="1m|3m|6m|1y|3y|5y|max"), refresh: bool = False):
    """Scheme metadata + NAV history (trimmed to `period`)."""
    detail = await service.get_scheme(code, refresh=refresh)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Scheme {code} not found")

    history = detail.get("nav_history", [])
    days = {"1m": 30, "3m": 91, "6m": 182, "1y": 365, "3y": 365 * 3, "5y": 365 * 5}.get(period)
    if days and len(history) > days:
        detail = {**detail, "nav_history": history[-days:]}
    return detail


@router.get("/{code}/returns")
async def get_returns(code: int, refresh: bool = False):
    """Trailing returns and CAGR (1M/3M/6M/1Y/3Y/5Y/inception)."""
    detail = await service.get_scheme(code, refresh=refresh)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Scheme {code} not found")
    return service.compute_returns(detail)


@router.get("/{code}/risk")
async def get_risk(code: int, refresh: bool = False):
    """Risk metrics: volatility, Sharpe, Sortino, max drawdown, grade."""
    detail = await service.get_scheme(code, refresh=refresh)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Scheme {code} not found")
    return service.compute_risk(detail)
