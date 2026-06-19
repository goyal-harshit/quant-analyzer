import asyncio
import logging
from typing import Optional
from datetime import datetime, timedelta

import httpx

logger = logging.getLogger(__name__)

class NseIndiaApiClient:
    """Wrapper around NseIndiaApi (nse[server]) for live NSE data.

    Uses server mode (httpx/http2) for Docker environments where
    yfinance (429) and nsepython (empty response) are blocked.
    Falls back gracefully to None on any error.
    """

    BASE_URL = "https://www.nseindia.com"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/market-data/live-equity-market",
    }

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._session_cookies: dict = {}
        self._cookie_ttl: Optional[datetime] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                http2=True,
                headers=self.HEADERS,
                follow_redirects=True,
                timeout=30.0,
            )
        return self._client

    async def _refresh_session(self):
        """Hit NSE homepage to get fresh session cookies."""
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.BASE_URL}/", headers=self.HEADERS)
            resp.raise_for_status()
            cookies = {c.name: c.value for c in client.cookies.jar}
            self._session_cookies = cookies
            self._cookie_ttl = datetime.utcnow() + timedelta(minutes=10)
            logger.info("NSE session refreshed, cookies=%s", list(cookies.keys()))
        except Exception as e:
            logger.warning("NSE session refresh failed: %s", e)
            self._session_cookies = {}
            self._cookie_ttl = None

    async def _ensure_session(self):
        if not self._session_cookies or (
            self._cookie_ttl and datetime.utcnow() > self._cookie_ttl
        ):
            await self._refresh_session()

    async def get_quote(self, symbol: str) -> Optional[dict]:
        """Fetch live quote for a single NSE symbol.

        Args:
            symbol: NSE symbol (e.g. 'RELIANCE', 'TCS')

        Returns:
            Dict with keys: lastPrice, change, pChange, open, high, low,
            previousClose, totalTradedVolume, lastUpdateTime
            or None on failure.
        """
        await self._ensure_session()
        if not self._session_cookies:
            logger.warning("No NSE session available, skipping quote for %s", symbol)
            return None

        url = (
            f"{self.BASE_URL}/api/quote-equity"
            f"?symbol={symbol.upper()}"
        )
        params = {
            "section": "trade_info",
        }
        try:
            client = await self._get_client()
            resp = await client.get(
                url,
                params=params,
                cookies=self._session_cookies,
            )
            resp.raise_for_status()
            data = resp.json()
            price_info = data.get("priceInfo", {})
            return {
                "lastPrice": price_info.get("lastPrice"),
                "change": price_info.get("change"),
                "pChange": price_info.get("pChange"),
                "open": price_info.get("open"),
                "high": price_info.get("intraDayHighLow", {}).get("max"),
                "low": price_info.get("intraDayHighLow", {}).get("min"),
                "previousClose": price_info.get("previousClose"),
                "totalTradedVolume": price_info.get("totalTradedVolume"),
                "lastUpdateTime": data.get("metadata", {}).get("lastUpdateTime"),
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning("NSE 403 for %s, refreshing session", symbol)
                self._session_cookies = {}
                self._cookie_ttl = None
                await self._refresh_session()
            else:
                logger.warning("NSE HTTP error for %s: %s", symbol, e)
        except Exception as e:
            logger.warning("NSE quote failed for %s: %s", symbol, e)
        return None

    async def get_quotes_batch(self, symbols: list[str]) -> dict[str, Optional[dict]]:
        """Fetch quotes for multiple symbols concurrently."""
        tasks = [self.get_quote(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out = {}
        for sym, res in zip(symbols, results):
            if isinstance(res, Exception):
                logger.warning("NSE quote for %s raised: %s", sym, res)
                out[sym] = None
            else:
                out[sym] = res
        return out

    async def get_history(self, symbol: str, days: int = 365) -> Optional[list[dict]]:
        """Fetch historical daily data for a symbol.

        Args:
            symbol: NSE symbol
            days: Number of days of history to fetch

        Returns:
            List of {date, open, high, low, close, volume} dicts
            or None on failure.
        """
        await self._ensure_session()
        if not self._session_cookies:
            return None

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        url = (
            f"{self.BASE_URL}/api/historical/securityArchives"
        )
        params = {
            "symbol": symbol.upper(),
            "from": start_date.strftime("%d-%m-%Y"),
            "to": end_date.strftime("%d-%m-%Y"),
            "dataType": "priceVolumeDeliverable",
            "series": "ALL",
        }
        try:
            client = await self._get_client()
            resp = await client.get(
                url,
                params=params,
                cookies=self._session_cookies,
            )
            resp.raise_for_status()
            data = resp.json()
            rows = []
            for entry in data.get("data", []):
                row = {
                    "date": entry.get("CH_TIMESTAMP"),
                    "open": entry.get("CH_OPENING_PRICE"),
                    "high": entry.get("CH_TRADE_HIGH_PRICE"),
                    "low": entry.get("CH_TRADE_LOW_PRICE"),
                    "close": entry.get("CH_CLOSING_PRICE"),
                    "volume": entry.get("CH_TOTAL_TRADED_QTY"),
                }
                if row["date"]:
                    rows.append(row)
            return rows
        except Exception as e:
            logger.warning("NSE history failed for %s: %s", symbol, e)
            return None

    async def get_market_status(self) -> Optional[dict]:
        """Check if NSE market is open.

        Returns dict with 'marketState', 'marketStatus' keys or None.
        """
        await self._ensure_session()
        if not self._session_cookies:
            return None
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{self.BASE_URL}/api/marketStatus",
                cookies=self._session_cookies,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "marketState": data.get("marketState"),
                "marketStatus": data.get("marketStatus"),
            }
        except Exception as e:
            logger.warning("NSE market status failed: %s", e)
            return None

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def __del__(self):
        if self._client and not self._client.is_closed:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._client.aclose())
                else:
                    loop.run_until_complete(self._client.aclose())
            except Exception:
                pass


nse_client = NseIndiaApiClient()
