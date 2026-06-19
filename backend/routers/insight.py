"""Insight Router — Consolidated stock insight endpoint.
Single API call replaces 4+ sequential calls for stock detail page.
All data sources fetched in parallel via agent-based dispatcher.
"""

import logging

from fastapi import APIRouter, Query

from services.insight_agent import insight_agent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{ticker}")
async def get_stock_insight(
    ticker: str,
    include_ai: bool = Query(default=False, description="Include AI-generated summary (adds ~2-5s)"),
):
    """Get full stock insight in one call — quote, fundamentals, history, technicals, factors, peers, AI."""
    result = await insight_agent.get_insight(ticker.upper(), include_ai=include_ai)
    return result
