"""
nse_live.py — minimal NSE India public-API client with cookie warming.

NSE blocks bare API requests (HTTP 403) but allows them once the client holds
the cookies set by loading the website first. This helper warms cookies on a
shared httpx client and refreshes them on 401/403. Used for live FII/DII flows
and IPO data — both of which NSE serves freely (no API key) and keeps current.
"""

from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://www.nseindia.com"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

_client: httpx.AsyncClient | None = None
_warmed_at: float = 0.0
_WARM_TTL = 600  # re-warm cookies every 10 min


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(12.0, connect=6.0),
            headers=_HEADERS,
            follow_redirects=True,
        )
    return _client


async def _warm(force: bool = False) -> None:
    global _warmed_at
    if not force and (time.time() - _warmed_at) < _WARM_TTL:
        return
    client = await _get_client()
    try:
        await client.get(_BASE, headers={**_HEADERS, "Accept": "text/html"})
        # A second hit on a report page solidifies the cookie set.
        await client.get(f"{_BASE}/option-chain", headers={**_HEADERS, "Accept": "text/html"})
        _warmed_at = time.time()
    except Exception as e:  # noqa: BLE001
        logger.warning("NSE cookie warm failed: %s", e)


async def get_json(path: str, referer: str | None = None) -> dict | list | None:
    """GET an NSE API path (e.g. '/api/fiidiiTradeReact'); returns parsed JSON or None."""
    url = path if path.startswith("http") else f"{_BASE}{path}"
    await _warm()
    client = await _get_client()
    headers = dict(_HEADERS)
    if referer:
        headers["Referer"] = referer
    for attempt in range(2):
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                ct = resp.headers.get("content-type", "")
                if "json" in ct or resp.text.strip()[:1] in "[{":
                    return resp.json()
                return None
            if resp.status_code in (401, 403):
                await _warm(force=True)
                continue
            logger.info("NSE %s -> HTTP %s", url, resp.status_code)
            return None
        except Exception as e:  # noqa: BLE001
            logger.info("NSE %s error: %s", url, e)
            await _warm(force=True)
    return None
