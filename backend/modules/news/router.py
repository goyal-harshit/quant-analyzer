"""News Router — real headlines + sentiment (Google News RSS, free)."""

from fastapi import APIRouter

from . import service

router = APIRouter()


@router.get("")
async def get_news(limit: int = 20):
    """Latest India market news with lexicon sentiment scores."""
    articles = await service.get_market_news(limit=limit)
    return {"articles": articles, "count": len(articles), "source": "Google News RSS"}


@router.get("/sentiment/{ticker}")
async def get_ticker_sentiment(ticker: str):
    """Recent news + aggregate sentiment for a specific ticker."""
    return await service.get_ticker_news(ticker)
