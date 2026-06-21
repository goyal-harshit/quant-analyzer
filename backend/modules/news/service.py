"""
News service — real headlines from Google News RSS (free, no API key) with a
lightweight lexicon sentiment score. Cached in Redis. No hardcoded data.
"""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from services.cache_service import cache

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(10.0, connect=6.0)
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
TTL_NEWS = 900  # 15 min

# Lightweight finance sentiment lexicon (no external dependency).
_POS = {
    "surge", "surges", "surged", "jump", "jumps", "gain", "gains", "rise", "rises",
    "rose", "profit", "profits", "beat", "beats", "up", "high", "record", "growth",
    "bullish", "upgrade", "upgraded", "strong", "outperform", "rally", "rallies",
    "soar", "soars", "soared", "boost", "wins", "win", "expand", "expansion", "buy",
    "positive", "rebound", "recover", "recovery", "milestone", "approval", "order",
}
_NEG = {
    "fall", "falls", "fell", "drop", "drops", "dropped", "plunge", "plunges", "loss",
    "losses", "miss", "misses", "missed", "down", "low", "weak", "bearish", "downgrade",
    "downgraded", "slump", "decline", "declines", "crash", "cut", "cuts", "fraud",
    "probe", "lawsuit", "fine", "penalty", "warn", "warning", "negative", "slowdown",
    "default", "scam", "raid", "ban", "sell", "selloff", "concern", "concerns", "risk",
}


def _score_text(text: str) -> float:
    words = re.findall(r"[a-z]+", (text or "").lower())
    p = sum(1 for w in words if w in _POS)
    n = sum(1 for w in words if w in _NEG)
    if p + n == 0:
        return 0.0
    return round((p - n) / (p + n), 2)


def _label(score: float) -> str:
    return "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"


async def _fetch_rss(query: str, limit: int = 20) -> list[dict]:
    url = (
        "https://news.google.com/rss/search?"
        f"q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    )
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True, headers=_HEADERS) as c:
            r = await c.get(url)
            if r.status_code != 200:
                logger.info("Google News RSS HTTP %s for %r", r.status_code, query)
                return []
            soup = BeautifulSoup(r.text, "lxml-xml")
            out = []
            for it in soup.find_all("item")[:limit]:
                title = it.title.text if it.title else ""
                if not title:
                    continue
                source = it.source.text if it.source else ""
                # Google prefixes "Title - Source"; strip the trailing source.
                clean_title = re.sub(r"\s+-\s+[^-]+$", "", title) if source and title.endswith(source) else title
                score = _score_text(clean_title)
                out.append({
                    "title": clean_title,
                    "url": it.link.text if it.link else "",
                    "source": source,
                    "published_at": it.pubDate.text if it.pubDate else "",
                    "sentiment_score": score,
                    "sentiment": _label(score),
                })
            return out
    except Exception as e:  # noqa: BLE001
        logger.info("Google News RSS error for %r: %s", query, e)
    return []


async def get_market_news(limit: int = 20) -> list[dict]:
    key = "news:market"
    cached = await cache.get(key)
    if cached:
        return json.loads(cached)[:limit]
    articles = await _fetch_rss("NSE India stock market Sensex Nifty", limit=25)
    if articles:
        await cache.set(key, json.dumps(articles), TTL_NEWS)
    return articles[:limit]


async def get_ticker_news(ticker: str, limit: int = 12) -> dict:
    t = ticker.upper()
    key = f"news:ticker:{t}"
    cached = await cache.get(key)
    if cached:
        return json.loads(cached)

    # Resolve a human company name for a better query.
    name = t
    try:
        from services.seed_data import _STOCK_MAP
        entry = _STOCK_MAP.get(t)
        if entry and len(entry) > 1 and entry[1]:
            name = entry[1]
    except Exception:
        pass

    articles = await _fetch_rss(f"{name} share price NSE", limit=limit)
    scores = [a["sentiment_score"] for a in articles]
    avg = round(sum(scores) / len(scores), 2) if scores else 0.0
    result = {
        "ticker": t,
        "name": name,
        "sentiment": _label(avg),
        "score": avg,
        "article_count": len(articles),
        "articles": articles,
    }
    if articles:
        await cache.set(key, json.dumps(result), TTL_NEWS)
    return result
