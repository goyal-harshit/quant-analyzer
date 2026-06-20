"""IPO router — /api/v1/ipo"""

import logging

from fastapi import APIRouter, Query

from . import service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def all_ipos(refresh: bool = False):
    """Every tracked IPO with computed status."""
    return {"ipos": await service.get_all(refresh)}


@router.get("/upcoming")
async def upcoming(refresh: bool = False):
    return {"ipos": await service.upcoming(refresh)}


@router.get("/open")
async def open_ipos(refresh: bool = False):
    return {"ipos": await service.open_ipos(refresh)}


@router.get("/listed")
async def listed(days: int = Query(60, ge=1, le=365), refresh: bool = False):
    return {"ipos": await service.listed(days, refresh)}


@router.get("/sme")
async def sme(refresh: bool = False):
    return {"ipos": await service.sme(refresh)}


@router.get("/calendar")
async def calendar(month: str | None = Query(None, description="yyyy-mm; defaults to current month")):
    return await service.calendar(month)
