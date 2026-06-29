"""
envelope.py — standard API response envelope (audit §3.3, P3).

A predictable ``{data, source, as_of, cached}`` shape lets the frontend render
provenance ("live" vs "cached as-of X" vs "seed") consistently across every
endpoint, instead of each route inventing its own ad-hoc fields.

Usage:
    return envelope(quote, source=quote.get("source"), cached=False)

Adopt incrementally — existing endpoints keep working; new/refactored ones can
wrap their payload in this for a uniform contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def envelope(
    data: Any,
    *,
    source: Optional[str] = None,
    as_of: Optional[str] = None,
    cached: bool = False,
) -> dict:
    """Wrap a payload in the standard response envelope.

    ``source``  — where the data came from (e.g. "yahoo", "seed", "cache").
    ``as_of``   — freshness timestamp; if the payload carries its own ``as_of``
                  it is reused, else now() is stamped.
    ``cached``  — whether this was served from a cache layer.
    """
    if as_of is None and isinstance(data, dict):
        as_of = data.get("as_of")
    return {
        "data": data,
        "source": source if source is not None else _source_of(data),
        "as_of": as_of or _now_iso(),
        "cached": cached,
    }


def _source_of(data: Any) -> Optional[str]:
    if isinstance(data, dict):
        return data.get("source")
    return None
