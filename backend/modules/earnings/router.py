"""Earnings Router — real quarterly results (screener.in)."""

from fastapi import APIRouter

from . import service

router = APIRouter()


@router.get("/calendar")
async def get_earnings_calendar():
    """Recently-reported quarterly results across the liquid universe."""
    return await service.get_calendar()


@router.get("/{ticker}/history")
async def get_earnings_history(ticker: str):
    """Latest reported quarterly figures for a ticker."""
    return await service.get_ticker_earnings(ticker)
