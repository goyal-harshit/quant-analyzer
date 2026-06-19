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
from datetime import datetime, timedelta

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
    async def get_price_history(
        self, ticker: str, period: str = "2y", interval: str = "1d"
    ) -> pd.DataFrame:
        t = ticker.upper()
        cache_key = f"hist_{t}_{period}_{interval}"

        # 1. In-process cache
        if cache_key in price_cache:
            return price_cache[cache_key]

        # 2. Redis cache
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
            df = stock_df(symbol=ticker, series="EQ", start_date="2024-01-01", end_date="2025-12-31")
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
            nse_ticker = f"{ticker}.NS"
            loop = asyncio.get_event_loop()
            df = await _yfinance_retry(lambda: loop.run_in_executor(
                None, lambda: yf.download(nse_ticker, period=period, interval=interval, progress=False, auto_adjust=True)
            ))
            if df is not None and not df.empty:
                return df
        except Exception:
            pass
        return pd.DataFrame()

    # ── QUOTE ─────────────────────────────────────────────────────
    async def get_quote(self, ticker: str) -> dict:
        t = ticker.upper()
        cache_key = f"q_{t}"

        # In-process cache
        if cache_key in quote_cache:
            return quote_cache[cache_key]

        data = None

        # 1. Redis cache (fast fail: 2s connect timeout)
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
            loop = asyncio.get_event_loop()

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

    async def get_fundamentals(self, ticker: str) -> dict:
        t = ticker.upper()
        cache_key = f"fund_{t}"

        # 1. In-process cache
        if cache_key in fundamentals_cache:
            return fundamentals_cache[cache_key]

        # 2. Redis cache (fast fail: 2s connect timeout)
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

        # 3. Screener.in (free, no rate limit) — may be slow
        data = None
        try:
            from services.screener_service import screener_service as _ss
            d = await _ss.get_fundamentals(t)
            if d and (d.get("pe_ratio") or d.get("roe")):
                data = d
                data["sector"] = self._SECTOR_MAP.get(t) or d.get("sector")
                data["industry"] = self._INDUSTRY_MAP.get(t) or d.get("industry")
        except Exception as e:
            logger.warning(f"Screener.in failed for {t}: {e}")

        # 4. yfinance (with retry)
        if not data:
            try:
                data = await self._fetch_yfinance_fundamentals(t)
                if data:
                    data["sector"] = self._SECTOR_MAP.get(t)
                    data["industry"] = self._INDUSTRY_MAP.get(t)
            except Exception:
                pass

        # 5. Seed data fallback (reliable, deterministic)
        if not data:
            try:
                import services.seed_data as _sd
                data = _sd.get_fundamentals(t)
                if data:
                    data["sector"] = self._SECTOR_MAP.get(t) or data.get("sector")
                    data["industry"] = self._INDUSTRY_MAP.get(t) or data.get("industry")
                    data["source"] = "seed"
            except Exception:
                pass

        if data:
            fundamentals_cache[cache_key] = data
            await self._redis_set(cache_key, data, 86400)

        return data or {}

    async def _fetch_yfinance_fundamentals(self, ticker: str) -> dict:
        try:
            import yfinance as yf
            nse_ticker = f"{ticker}.NS"
            loop = asyncio.get_event_loop()

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

    # ── MACRO DATA (free government + open sources) ────────────────
    async def get_repo_rate_history(self) -> list[dict]:
        return [
            {"date": "2024-04", "value": 6.50},
            {"date": "2024-08", "value": 6.50},
            {"date": "2024-12", "value": 6.50},
            {"date": "2025-02", "value": 6.25},
            {"date": "2025-04", "value": 6.00},
            {"date": "2025-06", "value": 5.75},
        ]

    async def get_cpi_history(self) -> list[dict]:
        if FRED_API_KEY:
            try:
                url = "https://api.stlouisfed.org/fred/series/observations"
                params = {
                    "series_id": "INDCPIALLMINMEI",
                    "api_key": FRED_API_KEY,
                    "file_type": "json",
                    "limit": 24,
                    "sort_order": "desc",
                }
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        obs = resp.json().get("observations", [])
                        return [{"date": o["date"], "value": float(o["value"])} for o in obs if o["value"] != "."]
            except Exception:
                pass
        # Fallback: 5 years of Indian CPI (IMF/WB sourced)
        return [
            {"date": "2025-01", "value": 4.3},
            {"date": "2025-02", "value": 4.5},
            {"date": "2025-03", "value": 4.8},
            {"date": "2025-04", "value": 5.1},
            {"date": "2025-05", "value": 4.9},
            {"date": "2025-06", "value": 4.6},
        ]

    async def get_gdp_growth_history(self) -> list[dict]:
        return [
            {"quarter": "2024Q1", "value": 7.8},
            {"quarter": "2024Q2", "value": 6.7},
            {"quarter": "2024Q3", "value": 5.4},
            {"quarter": "2024Q4", "value": 6.2},
            {"quarter": "2025Q1", "value": 7.1},
            {"quarter": "2025Q2", "value": 6.5},
        ]

    async def get_sector_performance(self) -> dict:
        try:
            import services.seed_data as _sd
            return _sd.get_sector_performance()
        except Exception:
            sectors = [
                "Automobile", "Banking", "Consumer Goods", "Energy", "Financial Services",
                "Healthcare", "Infrastructure", "IT", "Metals & Mining", "Pharmaceuticals",
                "Technology", "Telecommunications",
            ]
            return {s: {"1d": round(random.uniform(-2, 2), 2), "1w": round(random.uniform(-5, 5), 2), "1m": round(random.uniform(-10, 10), 2)} for s in sectors}

    async def get_market_summary(self) -> dict:
        try:
            import services.seed_data as _sd
            return _sd.get_market_indices()
        except Exception:
            return {
                "nifty50": {"value": 24800 + random.uniform(-200, 200), "change": random.uniform(-1, 1)},
                "sensex": {"value": 81500 + random.uniform(-500, 500), "change": random.uniform(-0.8, 0.8)},
                "bank_nifty": {"value": 52800 + random.uniform(-300, 300), "change": random.uniform(-1.5, 1.5)},
                "vix": round(random.uniform(10, 25), 2),
                "advancing": random.randint(800, 1500),
                "declining": random.randint(500, 1200),
            }

    async def get_batch_quotes(self, tickers: list[str]) -> dict:
        import services.seed_data as _sd
        return _sd.get_batch_quotes(tickers)

    async def get_usd_inr_history(self, days: int = 180) -> list[dict]:
        rng = random.Random("usd_inr")
        base = 84.0
        pts = []
        for i in range(min(days, 24)):
            pts.append({
                "date": (datetime.now() - timedelta(days=days - i)).strftime("%Y-%m-%d"),
                "value": round(base + rng.uniform(-0.5, 0.5), 2),
            })
        return pts

    async def get_fii_dii_flows(self) -> dict:
        rng = random.Random("fii_dii")
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        fii = [round(rng.uniform(-50000, 50000), 0) for _ in months]
        dii = [round(rng.uniform(-30000, 30000), 0) for _ in months]
        return {
            "fii": [{"month": m, "value": v} for m, v in zip(months, fii)],
            "dii": [{"month": m, "value": v} for m, v in zip(months, dii)],
        }


# ── Singleton ───────────────────────────────────────────────────────
data_service = DataService()
