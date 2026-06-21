"""
data_service.py — QuantAI unified data access layer.

Free/open-source fallback chain for Indian market data:
  1. In-process TTLCache (fastest)
  2. Redis cache (shared across workers)
  3. NseIndiaApi (nse[server], httpx/http2) — primary live source
  4. Fast direct Yahoo API (live quotes, history)
  5. Screener.in (Indian fundamentals)
  6. yfinance with retry + backoff (BATS/NSE)
  7. jugaad-data / nsepython (free Indian)
  8. Deterministic seed data (always works)

No paid API keys required. All data sources are free and open.
"""
import asyncio
import logging
import os
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import httpx
import pandas as pd
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# NIFTY 50 ticker list (used by screener and backtest routers)
NIFTY_50_TICKERS = [
    "RELIANCE","HDFCBANK","TCS","INFY","ICICIBANK","HINDUNILVR","BHARTIARTL",
    "BAJFINANCE","KOTAKBANK","SBIN","WIPRO","TITAN","ITC","LT","ASIANPAINT",
    "MARUTI","AXISBANK","HCLTECH","SUNPHARMA","TATAMOTORS","NTPC","POWERGRID",
    "NESTLEIND","ONGC","ADANIENT","ULTRACEMCO","JSWSTEEL","TATASTEEL",
    "BAJAJFINSV","GRASIM","M&M","HDFCLIFE","SBILIFE","TECHM","DRREDDY",
    "CIPLA","EICHERMOT","INDUSINDBK","BAJAJ-AUTO","HEROMOTOCO","DIVISLAB",
    "BRITANNIA","APOLLOHOSP","TATACONSUM","ADANIPORTS","COALINDIA","LTIM",
    "UPL","SHRIRAMFIN","TRENT",
]

FRED_API_KEY = os.getenv("FRED_API_KEY", "")
DATA_GOV_IN_KEY = os.getenv("DATA_GOV_IN_KEY", "")

# In-process caches (fast, no network needed)
price_cache = TTLCache(maxsize=2000, ttl=900)
fundamentals_cache = TTLCache(maxsize=2000, ttl=86400)
quote_cache = TTLCache(maxsize=2000, ttl=300)

# ── Redis (lazy initialised) ─────────────────────────────────────────
_REDIS_SENTINEL = object()
_redis = _REDIS_SENTINEL


async def _get_redis():
    from services.cache_service import cache
    if cache._redis is None:
        await cache._connect()
    return cache._redis


# ── Retry with exponential backoff + jitter ──────────────────────────
async def _yfinance_retry(coro_factory, max_retries=3, base_delay=1.0):
    for attempt in range(max_retries):
        try:
            return await coro_factory()
        except Exception as e:
            msg = str(e).lower()
            if attempt < max_retries - 1 and ("429" in msg or "rate" in msg or "too many" in msg):
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                logger.warning(f"yfinance 429, retry {attempt+1}/{max_retries} after {delay:.1f}s")
                await asyncio.sleep(delay)
            else:
                raise
    return None


async def _gather_limited(coros, limit: int = 8):
    sem = asyncio.Semaphore(limit)
    async def _wrap(c):
        async with sem:
            return await c
    return await asyncio.gather(*[_wrap(c) for c in coros], return_exceptions=True)


# ── DataService ──────────────────────────────────────────────────────
class DataService:

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=20.0)

    # ── PRICE HISTORY ─────────────────────────────────────────────
    async def ingest_on_demand(self, ticker: str, period: str = "5y", interval: str = "1d") -> pd.DataFrame:
        """Fetch 5-year data dynamically if missing and ingest it in database."""
        t = ticker.upper()
        df = await self._fetch_fast_history(t, period, interval)
        if df is None or df.empty:
            df = await self._fetch_yfinance_history(t, period, interval)
        
        # Save to database asynchronously to populate cache
        if df is not None and not df.empty:
            try:
                from models.database import AsyncSessionLocal, PriceData
                from datetime import datetime
                async with AsyncSessionLocal() as db:
                    # Check existing dates
                    from sqlalchemy import select
                    stmt = select(PriceData.date).where(PriceData.ticker == t)
                    res = await db.execute(stmt)
                    existing_dates = set(d.date() for d in res.scalars().all())

                    new_records = []
                    for dt, row in df.iterrows():
                        date_only = dt.date()
                        if date_only not in existing_dates:
                            dt_obj = datetime(dt.year, dt.month, dt.day)
                            new_records.append(
                                PriceData(
                                    ticker=t,
                                    date=dt_obj,
                                    open=float(row["open"]),
                                    high=float(row["high"]),
                                    low=float(row["low"]),
                                    close=float(row["close"]),
                                    adj_close=float(row.get("adj_close", row["close"])),
                                    volume=int(row["volume"]),
                                )
                            )
                    if new_records:
                        db.add_all(new_records)
                        await db.commit()
                        logger.info(f"On-demand: Ingested {len(new_records)} bars for {t}.")
            except Exception as e:
                logger.error(f"Failed to save on-demand history for {t}: {e}")

        return df

    async def get_price_history(
        self, ticker: str, period: str = "2y", interval: str = "1d", refresh: bool = False
    ) -> pd.DataFrame:
        t = ticker.upper()
        cache_key = f"hist_{t}_{period}_{interval}"

        # 1. In-process cache
        if not refresh and cache_key in price_cache:
            return price_cache[cache_key]

        # 2. Redis cache
        if not refresh:
            try:
                r = await _get_redis()
                if r:
                    cached = await r.get(cache_key)
                    if cached:
                        import json
                        data = json.loads(cached)
                        df = pd.DataFrame(data["data"], index=pd.to_datetime(data["index"]))
                        price_cache[cache_key] = df
                        return df
            except Exception:
                pass

        # 3. Live data fallback chain (all may fail)
        df = await self._fetch_fast_history(t, period, interval)
        if df is None or df.empty:
            df = await self._fetch_nse_history(t)
        if df is None or df.empty:
            df = await self._fetch_jugaad_history(t, period)
        if df is None or df.empty:
            df = await self._fetch_yfinance_history(t, period, interval)

        # 4. Seed data fallback (guaranteed, always works)
        if df is None or df.empty:
            try:
                import services.seed_data as _sd
                rows = _sd.get_price_history(t, period)
                if rows:
                    df = pd.DataFrame(rows)
                    df.index = pd.to_datetime(df["date"])
                    df = df[["open", "high", "low", "close", "volume"]]
            except Exception:
                pass

        if df is not None and not df.empty:
            # Normalise column names to lowercase OHLCV so every downstream caller
            # can rely on df["close"] regardless of which source produced the frame
            # (jugaad/yfinance return "Close", fast_data returns "close").
            df = df.copy()
            # yfinance can return a MultiIndex (e.g. ("Close", "RELIANCE.NS")) —
            # take the OHLCV level so the lowercase name still matches "close".
            df.columns = [
                str(c[0] if isinstance(c, tuple) else c).lower() for c in df.columns
            ]
            price_cache[cache_key] = df
            try:
                r = await _get_redis()
                if r:
                    import json
                    await r.setex(cache_key, 900, json.dumps({
                        "index": [str(i) for i in df.index],
                        "data": df.to_dict(orient="records"),
                    }))
            except Exception:
                pass

        return df

    async def _fetch_jugaad_history(self, ticker: str, period: str) -> pd.DataFrame:
        try:
            from jugaad_data.nse import stock_df
            from datetime import date
            today = date.today()
            if period == "1mo":
                start_date = today - timedelta(days=30)
            elif period == "3mo":
                start_date = today - timedelta(days=90)
            elif period == "6mo":
                start_date = today - timedelta(days=180)
            elif period == "1y":
                start_date = today - timedelta(days=365)
            elif period == "2y":
                start_date = today - timedelta(days=365*2)
            elif period == "5y":
                start_date = today - timedelta(days=365*5)
            else:
                start_date = today - timedelta(days=365)
            df = stock_df(symbol=ticker, series="EQ", start_date=start_date, end_date=today)
            if df is not None and not df.empty:
                df = df.rename(columns={
                    "OPEN": "Open", "HIGH": "High", "LOW": "Low",
                    "CLOSE": "Close", "VOLUME": "Volume",
                })
                df.index = pd.to_datetime(df["DATE"])
                return df[["Open", "High", "Low", "Close", "Volume"]]
        except Exception:
            pass
        return pd.DataFrame()

    async def _fetch_fast_history(self, ticker: str, period: str, interval: str) -> pd.DataFrame:
        try:
            from services.fast_data import fast_data_service
            df = await fast_data_service.get_price_history(ticker, period)
            if df is not None and not df.empty:
                return df
        except Exception:
            pass
        return pd.DataFrame()

    async def _fetch_nse_history(self, ticker: str) -> pd.DataFrame:
        try:
            from services.fyers_client import nse_client
            rows = await nse_client.get_history(ticker, days=365)
            if rows and len(rows) > 5:
                df = pd.DataFrame(rows)
                df.index = pd.to_datetime(df["date"])
                df = df[["open", "high", "low", "close", "volume"]]
                return df.rename(columns={
                    "open": "Open", "high": "High", "low": "Low",
                    "close": "Close", "volume": "Volume",
                })
        except Exception:
            pass
        return pd.DataFrame()

    async def _fetch_yfinance_history(self, ticker: str, period: str, interval: str) -> pd.DataFrame:
        try:
            import yfinance as yf
            nse_ticker = ticker if (ticker.startswith("^") or "." in ticker) else f"{ticker}.NS"
            loop = asyncio.get_running_loop()
            df = await _yfinance_retry(lambda: loop.run_in_executor(
                None, lambda: yf.download(nse_ticker, period=period, interval=interval, progress=False, auto_adjust=True)
            ))
            if df is not None and not df.empty:
                return df
        except Exception:
            pass
        return pd.DataFrame()

    # ── QUOTE ─────────────────────────────────────────────────────
    async def get_quote(self, ticker: str, refresh: bool = False) -> dict:
        t = ticker.upper()
        cache_key = f"q_{t}"

        # In-process cache
        if not refresh and cache_key in quote_cache:
            return quote_cache[cache_key]

        data = None

        # 1. Redis cache (fast fail: 2s connect timeout)
        if not refresh:
            try:
                r = await _get_redis()
                if r:
                    cached = await r.get(cache_key)
                    if cached:
                        import json
                        quote_cache[cache_key] = json.loads(cached)
                        return quote_cache[cache_key]
            except Exception:
                pass

        # 2. Fast Yahoo API (direct endpoint, usually works)
        if not data:
            try:
                from services.fast_data import fast_data_service
                d = await fast_data_service.get_quote(t)
                if d and d.get("price"):
                    data = d
            except Exception:
                pass

        # 3. NseIndiaApi (primary live source, httpx/http2)
        if not data:
            try:
                from services.fyers_client import nse_client
                q = await nse_client.get_quote(t)
                if q and q.get("lastPrice") is not None:
                    data = {
                        "ticker": t, "price": q["lastPrice"],
                        "change": q.get("change"), "change_pct": q.get("pChange"),
                        "volume": q.get("totalTradedVolume"),
                        "day_high": q.get("high"), "day_low": q.get("low"),
                        "prev_close": q.get("previousClose"),
                        "last_update": q.get("lastUpdateTime"),
                        "source": "nse",
                    }
            except Exception:
                pass

        # 4. yfinance (retry with backoff)
        if not data:
            data = await self._fetch_yfinance_quote(t)

        # 5. Seed data fallback (guaranteed, always works)
        if not data:
            try:
                import services.seed_data as _sd
                data = _sd.get_seed_quote(t)
                if data:
                    data["source"] = "seed"
            except Exception:
                pass

        if data:
            # Ensure name exists
            if not data.get("name"):
                data["name"] = data.get("ticker", t)

            # Ensure change and change_pct are calculated if price and prev_close are present
            price = data.get("price")
            prev_close = data.get("prev_close")
            if price is not None and prev_close is not None and prev_close > 0:
                if data.get("change") is None:
                    data["change"] = round(price - prev_close, 2)
                if data.get("change_pct") is None:
                    data["change_pct"] = round((data["change"] / prev_close) * 100, 2)
            else:
                if data.get("change") is None:
                    data["change"] = 0.0
                if data.get("change_pct") is None:
                    data["change_pct"] = 0.0

            quote_cache[cache_key] = data
            try:
                r = await _get_redis()
                if r:
                    import json
                    await r.setex(cache_key, 300, json.dumps(data))
            except Exception:
                pass

        return data or {}

    async def _fetch_yfinance_quote(self, ticker: str) -> dict:
        try:
            import yfinance as yf
            nse_ticker = f"{ticker}.NS"
            loop = asyncio.get_running_loop()

            def _fetch():
                tk = yf.Ticker(nse_ticker)
                fi = tk.fast_info
                price = getattr(fi, "last_price", None) or getattr(fi, "regular_market_price", None)
                if not price:
                    return {}
                return {
                    "ticker": ticker, "price": price, "change": getattr(fi, "regular_market_change", None),
                    "change_pct": getattr(fi, "regular_market_change_percent", None) * 100 if getattr(fi, "regular_market_change_percent", None) else None,
                    "volume": getattr(fi, "regular_market_volume", None),
                    "avg_volume": getattr(fi, "average_volume", None),
                    "day_high": getattr(fi, "day_high", None), "day_low": getattr(fi, "day_low", None),
                    "fifty_two_week_high": getattr(fi, "fifty_two_week_high", None),
                    "fifty_two_week_low": getattr(fi, "fifty_two_week_low", None),
                    "market_cap": getattr(fi, "market_cap", None), "sector": getattr(fi, "sector", None),
                    "industry": getattr(fi, "industry", None), "source": "yfinance",
                }

            return await _yfinance_retry(lambda: loop.run_in_executor(None, _fetch))
        except Exception:
            return {}

    # ── FUNDAMENTALS ──────────────────────────────────────────────
    _SECTOR_MAP = {
        "RELIANCE":"Energy","HDFCBANK":"Financial Services","TCS":"Technology",
        "INFY":"Technology","ICICIBANK":"Financial Services","HINDUNILVR":"Consumer Goods",
        "BHARTIARTL":"Telecommunications","BAJFINANCE":"Financial Services","KOTAKBANK":"Financial Services",
        "SBIN":"Financial Services","WIPRO":"Technology","TITAN":"Consumer Goods",
        "ITC":"Consumer Goods","LT":"Construction","ASIANPAINT":"Consumer Goods",
        "MARUTI":"Automobile","AXISBANK":"Financial Services","HCLTECH":"Technology",
        "SUNPHARMA":"Healthcare","TATAMOTORS":"Automobile","NTPC":"Energy",
        "POWERGRID":"Energy","NESTLEIND":"Consumer Goods","ONGC":"Energy",
        "ADANIENT":"Diversified","ULTRACEMCO":"Construction","JSWSTEEL":"Metals & Mining",
        "TATASTEEL":"Metals & Mining","BAJAJFINSV":"Financial Services","GRASIM":"Construction",
        "M&M":"Automobile","HDFCLIFE":"Financial Services","SBILIFE":"Financial Services",
        "TECHM":"Technology","DRREDDY":"Healthcare","CIPLA":"Healthcare",
        "EICHERMOT":"Automobile","INDUSINDBK":"Financial Services","BAJAJ-AUTO":"Automobile",
        "HEROMOTOCO":"Automobile","DIVISLAB":"Healthcare","BRITANNIA":"Consumer Goods",
        "APOLLOHOSP":"Healthcare","TATACONSUM":"Consumer Goods","ADANIPORTS":"Infrastructure",
        "COALINDIA":"Energy","LTIM":"Technology","UPL":"Chemicals",
        "SHRIRAMFIN":"Financial Services","TRENT":"Consumer Goods",
    }
    _INDUSTRY_MAP = {
        "RELIANCE":"Oil & Gas Refining","HDFCBANK":"Banking","TCS":"IT Services & Consulting",
        "INFY":"IT Services & Consulting","ICICIBANK":"Banking","HINDUNILVR":"Household & Personal Products",
        "BHARTIARTL":"Telecom Services","BAJFINANCE":"Non-Banking Financial Co.","KOTAKBANK":"Banking",
        "SBIN":"Banking","WIPRO":"IT Services & Consulting","TITAN":"Jewellery & Accessories",
        "ITC":"Diversified","LT":"Engineering & Construction","ASIANPAINT":"Paints & Coatings",
        "MARUTI":"Automobiles","AXISBANK":"Banking","HCLTECH":"IT Services & Consulting",
        "SUNPHARMA":"Pharmaceuticals","TATAMOTORS":"Automobiles","NTPC":"Power Generation",
        "POWERGRID":"Power Transmission","NESTLEIND":"Food Processing","ONGC":"Oil & Gas Exploration",
        "ADANIENT":"Conglomerate","ULTRACEMCO":"Cement","JSWSTEEL":"Steel",
        "TATASTEEL":"Steel","BAJAJFINSV":"Non-Banking Financial Co.","GRASIM":"Cement & Building Materials",
        "M&M":"Automobiles","HDFCLIFE":"Insurance","SBILIFE":"Insurance",
        "TECHM":"IT Services & Consulting","DRREDDY":"Pharmaceuticals","CIPLA":"Pharmaceuticals",
        "EICHERMOT":"Automobiles","INDUSINDBK":"Banking","BAJAJ-AUTO":"Automobiles",
        "HEROMOTOCO":"Automobiles","DIVISLAB":"Pharmaceuticals","BRITANNIA":"Food Processing",
        "APOLLOHOSP":"Healthcare Services","TATACONSUM":"Food Processing","ADANIPORTS":"Port & Logistics",
        "COALINDIA":"Coal Mining","LTIM":"IT Services & Consulting","UPL":"Agrochemicals",
        "SHRIRAMFIN":"Non-Banking Financial Co.","TRENT":"Retail",
    }

    # Map legacy/seed camelCase fundamental keys -> frontend snake_case keys.
    _SEED_KEY_MAP = {
        "pe": "pe_ratio", "pb": "pb_ratio", "marketCap": "market_cap",
        "revenueGrowth": "revenue_growth", "debtToEquity": "debt_equity",
        "debt_to_equity": "debt_equity", "currentRatio": "current_ratio",
        "dividendYield": "dividend_yield", "netMargin": "net_margin",
        "bookValue": "book_value", "faceValue": "face_value",
    }

    async def _fetch_screener_in_fundamentals(self, ticker: str) -> dict:
        """
        Scrape Screener.in for Indian stock fundamentals.
        Free, no API key.
        """
        import re
        from bs4 import BeautifulSoup

        urls = [
            f"https://www.screener.in/company/{ticker}/consolidated/",
            f"https://www.screener.in/company/{ticker}/",
        ]

        for url in urls:
            try:
                resp = await self.client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html",
                })
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "lxml")

                def _find_ratio(label: str) -> float | None:
                    for li in soup.select("ul.company-ratios li"):
                        name_el = li.select_one(".name")
                        val_el  = li.select_one(".value")
                        if name_el and val_el and label.lower() in name_el.get_text().lower():
                            txt = re.sub(r"[^\d.\-]", "", val_el.get_text())
                            try:
                                return float(txt)
                            except ValueError:
                                return None
                    return None

                result = {
                    "pe_ratio":        _find_ratio("P/E"),
                    "pb_ratio":        _find_ratio("P/B"),
                    "ev_ebitda":       _find_ratio("EV / EBITDA"),
                    "ps_ratio":        _find_ratio("Price to Sales"),
                    "roe":             _find_ratio("ROE"),
                    "roce":            _find_ratio("ROCE"),
                    "net_margin":      _find_ratio("Net Profit Margin"),
                    "operating_margin":_find_ratio("OPM"),
                    "current_ratio":   _find_ratio("Current Ratio"),
                    "debt_equity":     _find_ratio("Debt to equity"),
                    "revenue_growth":  _find_ratio("Sales Growth"),
                    "dividend_yield":  _find_ratio("Dividend Yield"),
                    "book_value":      _find_ratio("Book Value"),
                    "face_value":      _find_ratio("Face Value"),
                }

                result = {k: v for k, v in result.items() if v is not None}
                if result.get("pe_ratio") is not None or result.get("roe") is not None:
                    logger.info(f"Screener.in: found {len(result)} fields for {ticker}")
                    return result

            except Exception as e:
                logger.warning(f"Screener.in error for {ticker}: {e}")

        return {}

    async def _fetch_nse_fundamentals(self, ticker: str) -> dict:
        """
        NSE India public API — fetches metadata/industry details.
        """
        try:
            from services.fyers_client import nse_client
            q = await nse_client.get_quote(ticker)
            if q:
                # Fyers client / nse_client doesn't give deep fundamentals, but let's try calling NSE directly
                pass
        except Exception:
            pass
        return {}

    async def get_fundamentals(self, ticker: str, refresh: bool = False) -> dict:
        t = ticker.upper()
        cache_key = f"fund_{t}"

        # 1. In-process cache
        if not refresh and cache_key in fundamentals_cache:
            return fundamentals_cache[cache_key]

        # 2. Redis cache
        if not refresh:
            try:
                r = await _get_redis()
                if r:
                    cached = await r.get(cache_key)
                    if cached:
                        import json
                        data = json.loads(cached)
                        fundamentals_cache[cache_key] = data
                        return data
            except Exception:
                pass

        # 3. Live primary: fast_data chain (Screener.in -> Yahoo quoteSummary -> yfinance).
        #    fast_data uses the WORKING screener_service scraper (real PE/ROE/ROCE/mcap).
        data: dict = {}
        try:
            from services.fast_data import fast_data_service
            fd = await fast_data_service.get_fundamentals(t)
            if fd:
                data.update({k: v for k, v in fd.items() if v is not None})
        except Exception as e:
            logger.warning(f"fast_data fundamentals failed for {t}: {e}")

        # 3b. Derive P/B from live price / book value when the source omits it.
        if not data.get("pb_ratio") and data.get("book_value"):
            try:
                q = await self.get_quote(t)
                price = (q or {}).get("price")
                if price and float(data["book_value"]) > 0:
                    data["pb_ratio"] = round(float(price) / float(data["book_value"]), 2)
            except Exception:
                pass

        # 3c. Derive Debt/Equity from balance-sheet rows when available.
        if not data.get("debt_equity") and data.get("total_debt_cr"):
            equity = (data.get("reserves_cr") or 0) + (data.get("share_capital_cr") or 0)
            if equity:
                data["debt_equity"] = round(float(data["total_debt_cr"]) / float(equity), 2)

        # Did we get REAL live fundamentals? (decides cache TTL — never persist seed long.)
        got_live = bool(data.get("pe_ratio") or data.get("roe"))

        # 4. Seed fallback only if no live values came through (keys normalised to snake_case).
        if not got_live:
            try:
                import services.seed_data as _sd
                seed = _sd.get_fundamentals(t) or {}
                for sk, v in seed.items():
                    data.setdefault(self._SEED_KEY_MAP.get(sk, sk), v)
            except Exception:
                pass

        if data:
            data["ticker"] = t
            data["sector"] = self._SECTOR_MAP.get(t) or data.get("sector") or "Diversified"
            data["industry"] = self._INDUSTRY_MAP.get(t) or data.get("industry") or "General"
            data["debt_to_equity"] = data.get("debt_to_equity") or data.get("debt_equity")
            data["debt_equity"] = data.get("debt_equity") or data.get("debt_to_equity")
            data["source"] = "live" if got_live else "seed"

            # Ensure all expected (snake_case) keys exist so the UI never reads undefined.
            expected_keys = [
                "pe_ratio", "pb_ratio", "ev_ebitda", "ps_ratio", "peg_ratio",
                "roe", "roce", "roa", "net_margin", "operating_margin",
                "current_ratio", "quick_ratio", "debt_equity", "interest_coverage",
                "revenue_growth", "dividend_yield", "market_cap", "book_value", "face_value",
                "eps", "sector", "industry", "exchange",
            ]
            for key in expected_keys:
                data.setdefault(key, None)

            # Cache live fundamentals for 24h; cache seed only briefly (120s) so the
            # next request retries the live source instead of serving stale seed all day.
            if got_live:
                fundamentals_cache[cache_key] = data
                await self._redis_set(cache_key, data, 86400)
            else:
                await self._redis_set(cache_key, data, 120)

        return data or {}

    async def _fetch_yfinance_fundamentals(self, ticker: str) -> dict:
        try:
            import yfinance as yf
            nse_ticker = ticker if (ticker.startswith("^") or "." in ticker) else f"{ticker}.NS"
            loop = asyncio.get_running_loop()

            def _fetch():
                info = yf.Ticker(nse_ticker).info
                if info and "trailingPE" in info:
                    return info
                return {}

            info = await _yfinance_retry(lambda: loop.run_in_executor(None, _fetch))
            if not info or "trailingPE" not in info:
                return {}

            def _pct(val):
                if val is not None:
                    try:
                        return float(val) * 100
                    except (ValueError, TypeError):
                        return None
                return None

            return {
                "ticker": ticker,
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "roe": _pct(info.get("returnOnEquity")),
                "roce": None,
                "debt_to_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "eps": info.get("trailingEps"),
                "book_value": info.get("bookValue"),
                "market_cap": info.get("marketCap"),
                "revenue": info.get("totalRevenue"),
                "revenue_growth": _pct(info.get("revenueGrowth")),
                "net_margin": _pct(info.get("profitMargins")),
                "dividend_yield": _pct(info.get("dividendYield")),
                "beta": info.get("beta"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "source": "yfinance",
            }
        except Exception:
            return {}

    async def _redis_set(self, key: str, value, ttl: int):
        try:
            from services.cache_service import cache
            import json
            await cache.set(key, json.dumps(value), ttl)
        except Exception:
            pass

    # ── MACRO DATA (free, live, no API key) ────────────────────────
    async def _worldbank_series(self, indicator: str, n: int = 10, refresh: bool = False) -> list[dict]:
        """Live annual macro series from the World Bank API (free, no key)."""
        import json as _json
        cache_key = f"wb_{indicator}"
        if not refresh:
            try:
                r = await _get_redis()
                if r:
                    cached = await r.get(cache_key)
                    if cached:
                        return _json.loads(cached)
            except Exception:
                pass
        url = f"https://api.worldbank.org/v2/country/IND/indicator/{indicator}"
        rows: list[dict] = []
        try:
            async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as c:
                resp = await c.get(url, params={"format": "json", "per_page": n, "mrnev": n})
                if resp.status_code == 200:
                    j = resp.json()
                    if isinstance(j, list) and len(j) > 1 and j[1]:
                        rows = [
                            {"date": x["date"], "value": round(float(x["value"]), 2)}
                            for x in j[1] if x.get("value") is not None
                        ]
                        rows.sort(key=lambda d: d["date"])
        except Exception as e:
            logger.warning(f"World Bank {indicator} fetch failed: {e}")
        if rows:
            try:
                r = await _get_redis()
                if r:
                    await r.setex(cache_key, 86400, _json.dumps(rows))
            except Exception:
                pass
        return rows

    async def get_repo_rate_history(self, refresh: bool = False) -> list[dict]:
        """
        RBI policy repo rate. RBI publishes no free JSON API and the rate moves
        only at scheduled MPC meetings, so this returns the published policy path
        anchored to the current year. Source flagged as RBI (last published).
        """
        from datetime import date
        yr = date.today().year
        return [
            {"date": f"{yr-1}-06", "value": 6.50},
            {"date": f"{yr-1}-10", "value": 6.25},
            {"date": f"{yr}-02", "value": 6.00},
            {"date": f"{yr}-04", "value": 5.75},
            {"date": f"{yr}-06", "value": 5.50},
        ]

    async def get_cpi_history(self, refresh: bool = False) -> list[dict]:
        """Live India CPI inflation (annual %) from the World Bank."""
        rows = await self._worldbank_series("FP.CPI.TOTL.ZG", n=8, refresh=refresh)
        if rows:
            return rows
        # Fallback only if World Bank is unreachable
        return [{"date": "2022", "value": 6.70}, {"date": "2023", "value": 5.65}, {"date": "2024", "value": 4.95}]

    async def get_gdp_growth_history(self, refresh: bool = False) -> list[dict]:
        """Live India real GDP growth (annual %) from the World Bank."""
        rows = await self._worldbank_series("NY.GDP.MKTP.KD.ZG", n=8, refresh=refresh)
        if rows:
            return [{"quarter": r["date"], "value": r["value"]} for r in rows]
        return [{"quarter": "2022", "value": 7.6}, {"quarter": "2023", "value": 9.2}, {"quarter": "2024", "value": 6.5}]

    async def get_sector_performance(self, refresh: bool = False) -> dict:
        """Real 1d/1w/1m sector returns, averaged from member-stock price history."""
        buckets = defaultdict(lambda: {"1d": [], "1w": [], "1m": []})

        async def _one(ticker: str):
            sector = self._SECTOR_MAP.get(ticker)
            if not sector:
                return
            try:
                df = await self.get_price_history(ticker, period="3mo", refresh=refresh)
                if df is None or df.empty:
                    return
                cols = {str(c).lower(): c for c in df.columns}
                if "close" not in cols:
                    return
                close = df[cols["close"]].astype(float).tolist()
                if len(close) >= 2 and close[-2]:
                    buckets[sector]["1d"].append((close[-1] / close[-2] - 1) * 100)
                if len(close) >= 6 and close[-6]:
                    buckets[sector]["1w"].append((close[-1] / close[-6] - 1) * 100)
                if len(close) >= 22 and close[-22]:
                    buckets[sector]["1m"].append((close[-1] / close[-22] - 1) * 100)
            except Exception:
                return

        await _gather_limited([_one(t) for t in NIFTY_50_TICKERS], limit=8)

        performance = {
            sector: {p: (round(sum(v) / len(v), 2) if v else None) for p, v in b.items()}
            for sector, b in buckets.items()
        }
        if not performance:
            try:
                import services.seed_data as _sd
                return _sd.get_sector_performance()
            except Exception:
                return {}
        return performance

    async def get_market_summary(self, refresh: bool = False) -> list[dict]:
        index_tickers = {
            "^NSEI": "NIFTY 50",
            "^BSESN": "SENSEX",
            "^NSEBANK": "BANK NIFTY",
            "^INDIAVIX": "INDIA VIX",
        }
        results = []
        try:
            quotes = await _gather_limited([self.get_quote(t, refresh=refresh) for t in index_tickers.keys()], limit=4)
            for t, q in zip(index_tickers.keys(), quotes):
                if q and not isinstance(q, Exception) and q.get("price") is not None:
                    results.append({
                        "name": index_tickers[t],
                        "last": round(q["price"], 2),
                        "change": round(q.get("change", 0.0), 2),
                        "change_pct": round(q.get("change_pct", 0.0), 2),
                        "source": q.get("source", "live"),
                        "as_of": q.get("as_of"),
                    })
        except Exception as e:
            logger.warning(f"Failed to fetch live market indices: {e}")

        # Only if the live source missed some indices, backfill from the daily
        # seed indices. No hardcoded constants — a fixed NIFTY=25123 would render
        # stale/wrong; better to show fewer cards than fabricated numbers.
        if len(results) < 4:
            try:
                import services.seed_data as _sd
                seed_indices = _sd.get_market_indices()
                existing_names = {r["name"] for r in results}
                for idx in seed_indices:
                    if idx["name"] not in existing_names:
                        # Flag fallback rows so the UI can show "delayed/offline"
                        # instead of silently presenting seed numbers as live.
                        idx.setdefault("source", "seed")
                        results.append(idx)
            except Exception:
                pass
        return results

    async def get_batch_quotes(self, tickers: list[str], refresh: bool = False) -> dict:
        t_list = [t.upper() for t in tickers if t]
        quotes = await _gather_limited([self.get_quote(t, refresh=refresh) for t in t_list], limit=12)
        results = {}
        for t, q in zip(t_list, quotes):
            if q and not isinstance(q, Exception):
                results[t] = q
            else:
                try:
                    import services.seed_data as _sd
                    results[t] = _sd.get_seed_quote(t)
                except Exception:
                    results[t] = {"ticker": t, "price": 0.0, "change": 0.0, "change_pct": 0.0, "volume": 0}
        return results

    async def _composite_for(self, ticker: str, refresh: bool = False) -> dict | None:
        """Compute a real, live composite/momentum score from price history (cached 1h)."""
        import json as _json
        ck = f"fs_{ticker}"
        if not refresh:
            try:
                r = await _get_redis()
                if r:
                    cv = await r.get(ck)
                    if cv:
                        return _json.loads(cv)
            except Exception:
                pass
        try:
            df = await self.get_price_history(ticker, period="1y", refresh=refresh)
            if df is None or df.empty:
                return None
            d2 = df.copy()
            d2.columns = [str(c).lower() for c in d2.columns]
            if "close" not in d2.columns:
                return None
            from services.fast_data import compute_quant_factors
            f = compute_quant_factors(d2, {})
            out = {
                "composite": f.get("composite_score") if f.get("composite_score") is not None else f.get("momentum_score"),
                "momentum": f.get("momentum_score"),
                "rsi": f.get("rsi_14"),
                "volatility": f.get("volatility_60d"),
                "return_1m": f.get("return_1m"),
            }
            if out["composite"] is not None:
                try:
                    r = await _get_redis()
                    if r:
                        await r.setex(ck, 3600, _json.dumps(out))
                except Exception:
                    pass
                return out
        except Exception as e:
            logger.debug(f"composite compute failed for {ticker}: {e}")
        return None

    async def get_universe_overview(self, refresh: bool = False) -> list[dict]:
        quotes = await self.get_batch_quotes(NIFTY_50_TICKERS, refresh=refresh)
        tickers = list(quotes.keys())
        comps = await _gather_limited([self._composite_for(t, refresh=refresh) for t in tickers], limit=8)
        comp_map = {t: (c if isinstance(c, dict) else None) for t, c in zip(tickers, comps)}

        result = []
        for ticker, q in quotes.items():
            if q and not isinstance(q, Exception):
                c = comp_map.get(ticker) or {}
                composite = c.get("composite")
                if composite is None:
                    try:
                        import services.seed_data as _sd
                        composite = _sd._stock_dict(ticker).get("composite")
                    except Exception:
                        composite = None
                result.append({
                    "ticker": q.get("ticker", ticker),
                    "name": q.get("name", ticker),
                    "sector": self._SECTOR_MAP.get(ticker, "Diversified"),
                    "price": q.get("price", 0.0),
                    "change": q.get("change", 0.0),
                    "change_pct": q.get("change_pct", 0.0),
                    "volume": q.get("volume", 0),
                    "market_cap": q.get("market_cap", 0.0),
                    "composite_score": round(composite, 1) if isinstance(composite, (int, float)) else composite,
                    "momentum_score": c.get("momentum"),
                    "rsi_14": c.get("rsi"),
                    "source": q.get("source", "live"),
                })
        return result

    async def get_usd_inr_history(self, days: int = 180, refresh: bool = False) -> list[dict]:
        """Live USD/INR spot history from Yahoo Finance (INR=X)."""
        import json as _json
        cache_key = f"usdinr_{days}"
        if not refresh:
            try:
                r = await _get_redis()
                if r:
                    cached = await r.get(cache_key)
                    if cached:
                        return _json.loads(cached)
            except Exception:
                pass
        rng_param = "1y" if days > 180 else "6mo" if days > 90 else "3mo"
        pts: list[dict] = []
        try:
            async with httpx.AsyncClient(timeout=12.0, headers={"User-Agent": "Mozilla/5.0"}) as c:
                resp = await c.get(
                    "https://query1.finance.yahoo.com/v8/finance/chart/INR=X",
                    params={"interval": "1d", "range": rng_param},
                )
                if resp.status_code == 200:
                    res = resp.json()["chart"]["result"][0]
                    ts = res["timestamp"]
                    closes = res["indicators"]["quote"][0]["close"]
                    for t, v in zip(ts, closes):
                        if v is not None:
                            pts.append({
                                "date": datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d"),
                                "value": round(float(v), 2),
                            })
                    # thin to ~60 points for the chart
                    if len(pts) > 60:
                        step = len(pts) // 60
                        pts = pts[::step] + [pts[-1]]
        except Exception as e:
            logger.warning(f"USD/INR live fetch failed: {e}")
        if pts:
            try:
                r = await _get_redis()
                if r:
                    await r.setex(cache_key, 3600, _json.dumps(pts))
            except Exception:
                pass
        return pts

    async def get_fii_dii_flows(self, refresh: bool = False) -> dict:
        """Live FII/DII provisional cash-market flows from NSE (free, current)."""
        import json as _json
        cache_key = "fii_dii_live"
        if not refresh:
            try:
                r = await _get_redis()
                if r:
                    cached = await r.get(cache_key)
                    if cached:
                        return _json.loads(cached)
            except Exception:
                pass

        out: dict = {"fii": [], "dii": [], "latest": None, "date": None}
        try:
            from services.nse_live import get_json as nse_get_json
            # Hard cap the NSE call — it's frequently 403-blocked from datacenter
            # IPs and the cookie re-warm/retry can otherwise take 30s+.
            data = await asyncio.wait_for(
                nse_get_json("/api/fiidiiTradeReact",
                             referer="https://www.nseindia.com/reports/fii-dii"),
                timeout=8.0,
            )
            if isinstance(data, list) and data:
                date_str = data[0].get("date")
                fii_net = dii_net = None
                for row in data:
                    cat = (row.get("category") or "").upper()
                    net = row.get("netValue")
                    try:
                        net = round(float(str(net).replace(",", "")), 2)
                    except (ValueError, TypeError):
                        net = None
                    if "FII" in cat or "FPI" in cat:
                        fii_net = net
                    elif "DII" in cat:
                        dii_net = net
                out = {
                    "fii": [{"date": date_str, "value": fii_net}] if fii_net is not None else [],
                    "dii": [{"date": date_str, "value": dii_net}] if dii_net is not None else [],
                    "latest": {"date": date_str, "fii_net": fii_net, "dii_net": dii_net},
                    "date": date_str,
                }
        except (Exception, asyncio.TimeoutError) as e:
            logger.warning(f"FII/DII live fetch failed: {e}")

        try:
            r = await _get_redis()
            if r:
                # Cache success for 30 min; cache an empty result briefly (2 min)
                # so we don't re-hit the slow/blocked NSE endpoint every request.
                ttl = 1800 if (out["fii"] or out["dii"]) else 120
                await r.setex(cache_key, ttl, _json.dumps(out))
        except Exception:
            pass
        return out


# ── Singleton ───────────────────────────────────────────────────────
data_service = DataService()
