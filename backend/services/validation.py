"""
validation.py — shared input validation helpers.

Centralises ticker validation so untrusted path/query input can't reach
downstream services (data fetchers, LLM prompts, scrapers) as a path-traversal
payload or prompt-injection vector.
"""

import re

from fastapi import HTTPException

# NSE/BSE symbols: uppercase alphanumerics with a few allowed punctuation chars
# (e.g. M&M, BAJAJ-AUTO, RELIANCE.NS, 500325.BO). Index symbols start with '^'.
_TICKER_RE = re.compile(r"^\^?[A-Z0-9][A-Z0-9&\-\.]{0,19}$")


def validate_ticker(ticker: str) -> str:
    """Normalise and validate a ticker symbol. Raises HTTP 400 if malformed.

    Returns the upper-cased, stripped ticker so callers can use the result
    directly instead of re-normalising.
    """
    if not ticker or not isinstance(ticker, str):
        raise HTTPException(status_code=400, detail="Ticker is required")
    t = ticker.strip().upper()
    if not _TICKER_RE.match(t):
        raise HTTPException(status_code=400, detail=f"Invalid ticker symbol: {ticker!r}")
    return t
