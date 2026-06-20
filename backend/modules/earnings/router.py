"""Earnings Router — Earnings center endpoints"""

from fastapi import APIRouter
from services.data_service import data_service

router = APIRouter()


@router.get("/calendar")
async def get_earnings_calendar():
    """Get upcoming earnings calendar (placeholder for production)."""
    return {
        "upcoming": [],
        "message": "Earnings calendar not yet connected. Connect NSE/BSE corporate announcements API.",
    }


@router.get("/{ticker}/history")
async def get_earnings_history(ticker: str):
    """Get earnings history for a ticker."""
    return {
        "ticker": ticker.upper(),
        "history": [],
        "message": "Earnings history not yet connected. Connect SEC EDGAR or NSE announcements.",
    }
