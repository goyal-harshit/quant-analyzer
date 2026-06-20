"""News Router — News intelligence endpoints"""

from fastapi import APIRouter
from services.data_service import data_service

router = APIRouter()


@router.get("")
async def get_news():
    """Get latest news with sentiment scores (placeholder for production)."""
    return {
        "articles": [],
        "message": "News ingestion pipeline not yet connected. Connect SEC EDGAR, NSE announcements, or RSS feeds.",
    }


@router.get("/sentiment/{ticker}")
async def get_ticker_sentiment(ticker: str):
    """Get sentiment analysis for a specific ticker."""
    return {
        "ticker": ticker.upper(),
        "sentiment": "neutral",
        "score": 0.0,
        "articles": [],
    }
