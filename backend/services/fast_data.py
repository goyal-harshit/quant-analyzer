"""
Fast Data Service — Direct Yahoo Finance API (no yfinance library)
===================================================================
Bypasses the yfinance library's rate limiting by calling Yahoo Finance
API endpoints directly via httpx. Works reliably from Docker containers.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
import numpy as np
import pandas as pd

from services.reliability import SOURCE_DOWN_STATUS, CircuitOpenError, guard_call

logger = logging.getLogger(__name__)

YAHOO_BASE = "https://query1.finance.yahoo.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


class FastDataService:
    """
    Direct Yahoo Finance API calls, guarded by a per-source circuit breaker +
    rate limiter so repeated 429/403s trip the breaker instead of stampeding.
    """

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=12.0, headers=HEADERS)

    async def _get(self, url: str, params: dict = None) -> Optional[dict]:
        async def _fetch() -> Optional[dict]:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in SOURCE_DOWN_STATUS:
                # Raise so the breaker counts this against Yahoo's health.
                raise httpx.HTTPStatusError(
                    f"Yahoo HTTP {resp.status_code}", request=resp.request, response=resp
                )
            # Data-absent (404/400/etc.): healthy source, no data — don't trip.
            return None

        try:
            return await guard_call("yahoo", _fetch)
        except CircuitOpenError as e:
            logger.warning("Yahoo circuit open, skipping fetch: %s", e)
        except Exception as e:
            logger.warning(f"Yahoo API error: {e}")
        return None

    # ── PRICE HISTORY ─────────────────────────────────────────────
    async def get_price_history(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """Fetch OHLCV history directly from Yahoo Finance chart API."""
        period_map = {"1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y"}
        range_val = period_map.get(period, "1y")

        formatted = ticker.upper()
        if not (formatted.startswith("^") or "." in formatted):
            formatted_ns = f"{formatted}.NS"
        else:
            formatted_ns = formatted

        data = await self._get(
            f"{YAHOO_BASE}/v8/finance/chart/{formatted_ns}",
            params={"interval": "1d", "range": range_val, "includePrePost": "false"}
        )
        if (not data or not data.get("chart", {}).get("result")) and not (formatted.startswith("^") or "." in formatted):
            # Try BSE
            data = await self._get(
                f"{YAHOO_BASE}/v8/finance/chart/{formatted}.BO",
                params={"interval": "1d", "range": range_val, "includePrePost": "false"}
            )
        if not data or not data.get("chart", {}).get("result"):
            return pd.DataFrame()

        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]

        df = pd.DataFrame({
            "open": quotes["open"],
            "high": quotes["high"],
            "low": quotes["low"],
            "close": quotes["close"],
            "volume": quotes["volume"],
        }, index=pd.to_datetime(timestamps, unit="s"))

        df = df.dropna(subset=["close"])
        return df

    # ── SYMBOL SEARCH ─────────────────────────────────────────────
    async def search(self, q: str, limit: int = 15) -> list[dict]:
        """Search ANY listed NSE/BSE stock via Yahoo's search API (covers the
        whole market, not a hardcoded list). NSE (.NS) preferred over BSE (.BO)."""
        q = (q or "").strip()
        if not q:
            return []
        data = await self._get(
            f"{YAHOO_BASE}/v1/finance/search",
            params={"q": q, "quotesCount": 20, "newsCount": 0, "enableFuzzyQuery": "true"},
        )
        out: list[dict] = []
        seen: set[str] = set()
        for it in (data or {}).get("quotes", []) or []:
            # Equities only — exclude Yahoo's mutual-fund (0P…), ETF and index hits.
            if (it.get("quoteType") or "").upper() != "EQUITY":
                continue
            sym = (it.get("symbol") or "").upper()
            exch = (it.get("exchange") or "").upper()
            is_nse = sym.endswith(".NS") or exch == "NSI"
            is_bse = sym.endswith(".BO") or exch == "BSE"
            if not (is_nse or is_bse):
                continue
            ticker = sym.replace(".NS", "").replace(".BO", "")
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            out.append({
                "ticker": ticker,
                "name": it.get("shortname") or it.get("longname") or ticker,
                "sector": it.get("sector") or it.get("sectorDisp") or "",
                "exchange": "NSE" if is_nse else "BSE",
            })
            if len(out) >= limit:
                break
        return out

    # ── LIVE QUOTE ────────────────────────────────────────────────
    async def get_quote(self, ticker: str) -> dict:
        """Fetch current quote from Yahoo Finance chart API (1d range)."""
        formatted = ticker.upper()
        if not (formatted.startswith("^") or "." in formatted):
            formatted_ns = f"{formatted}.NS"
        else:
            formatted_ns = formatted

        # range=1d → meta.chartPreviousClose is the *prior trading session's* close,
        # which is exactly the baseline for the daily change. (A 5d range made
        # chartPreviousClose ~5 days old, and deriving prev-close from the candle
        # series broke when the live price drifted from the last candle's close,
        # mislabelling the current session as already-closed.)
        data = await self._get(
            f"{YAHOO_BASE}/v8/finance/chart/{formatted_ns}",
            params={"interval": "1d", "range": "1d", "includePrePost": "false"}
        )
        if (not data or not data.get("chart", {}).get("result")) and not (formatted.startswith("^") or "." in formatted):
            # Try BSE
            data = await self._get(
                f"{YAHOO_BASE}/v8/finance/chart/{formatted}.BO",
                params={"interval": "1d", "range": "1d", "includePrePost": "false"}
            )
        if not data or not data.get("chart", {}).get("result"):
            return {}

        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("chartPreviousClose") or meta.get("previousClose") or 0
        # Fallback only if meta omits the prior close.
        if not prev_close:
            try:
                closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
                if closes:
                    prev_close = closes[-2] if len(closes) >= 2 else closes[-1]
            except Exception:
                pass
        if not price:
            price = prev_close

        # Guard on prev_close only — a 0.0 change is a valid value, not "missing".
        change = round(price - prev_close, 2) if (price and prev_close) else 0.0
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0.0

        market_time = meta.get("regularMarketTime")
        as_of = (
            datetime.fromtimestamp(market_time, tz=timezone.utc).isoformat()
            if market_time else None
        )

        return {
            "ticker": ticker,
            "name": meta.get("shortName", meta.get("longName", ticker)),
            "price": price,
            "prev_close": prev_close,
            "source": "live",
            "as_of": as_of,
            "change": change,
            "change_pct": change_pct,
            "open": meta.get("regularMarketDayOpen", 0),
            "day_high": meta.get("regularMarketDayHigh", 0),
            "day_low": meta.get("regularMarketDayLow", 0),
            "volume": meta.get("regularMarketVolume", 0),
            "market_cap": meta.get("marketCap", 0),
            "fifty_two_week_high": meta.get("fiftyTwoWeekHigh", 0),
            "fifty_two_week_low": meta.get("fiftyTwoWeekLow", 0),
            "fifty_day_avg": meta.get("fiftyDayAverage", 0),
            "two_hundred_day_avg": meta.get("twoHundredDayAverage", 0),
            "year_change_pct": meta.get("yearChange", 0) * 100 if meta.get("yearChange") else 0.0,
            "currency": meta.get("currency", "INR"),
            "exchange": meta.get("exchangeName", "NSE"),
        }

    async def get_yahoo_quote_summary(self, ticker: str) -> dict:
        """
        Fetch fundamentals directly from Yahoo Finance quoteSummary API.
        Free, direct, bypasses Ticker.info rate limits.
        """
        formatted = ticker.upper()
        if not (formatted.startswith("^") or "." in formatted):
            formatted_ns = f"{formatted}.NS"
        else:
            formatted_ns = formatted

        modules = "summaryDetail,financialData,defaultKeyStatistics"
        url = f"{YAHOO_BASE}/v10/finance/quoteSummary/{formatted_ns}"
        
        try:
            data = await self._get(url, params={"modules": modules})
            if not data or not data.get("quoteSummary", {}).get("result"):
                if not (formatted.startswith("^") or "." in formatted):
                    # Try BSE
                    data = await self._get(
                        f"{YAHOO_BASE}/v10/finance/quoteSummary/{formatted}.BO",
                        params={"modules": modules}
                    )
            
            if not data or not data.get("quoteSummary", {}).get("result"):
                return {}
                
            res = data["quoteSummary"]["result"][0]
            
            summary_detail = res.get("summaryDetail", {})
            financial_data = res.get("financialData", {})
            key_stats = res.get("defaultKeyStatistics", {})
            
            def _val(obj, key):
                val = obj.get(key, {})
                if isinstance(val, dict):
                    return val.get("raw")
                return None
                
            def _pct_val(obj, key):
                val = _val(obj, key)
                if val is not None:
                    return val * 100
                return None

            return {
                "ticker": ticker,
                "pe_ratio": _val(summary_detail, "trailingPE"),
                "forward_pe": _val(summary_detail, "forwardPE"),
                "pb_ratio": _val(key_stats, "priceToBook"),
                "ps_ratio": _val(summary_detail, "priceToSalesTrailing12Months"),
                "ev_ebitda": _val(key_stats, "enterpriseValToEbitda"),
                "peg_ratio": _val(key_stats, "pegRatio"),
                "roe": _pct_val(financial_data, "returnOnEquity"),
                "roa": _pct_val(financial_data, "returnOnAssets"),
                "gross_margin": _pct_val(financial_data, "grossMargins"),
                "ebitda_margin": _pct_val(financial_data, "ebitdaMargins"),
                "net_margin": _pct_val(financial_data, "profitMargins"),
                "operating_margin": _pct_val(financial_data, "operatingMargins"),
                "revenue_growth": _pct_val(financial_data, "revenueGrowth"),
                "earnings_growth": _pct_val(financial_data, "earningsGrowth"),
                "debt_equity": _val(financial_data, "debtToEquity"),
                "current_ratio": _val(financial_data, "currentRatio"),
                "free_cashflow": _val(financial_data, "freeCashflow"),
                "beta": _val(key_stats, "beta"),
                "dividend_yield": _pct_val(summary_detail, "dividendYield"),
                "market_cap": _val(summary_detail, "marketCap") or _val(key_stats, "marketCap"),
                "enterprise_value": _val(financial_data, "enterpriseValue"),
                "book_value": _val(key_stats, "bookValue"),
            }
        except Exception as e:
            logger.warning(f"Error fetching Yahoo quote summary for {ticker}: {e}")
            return {}

    # ── FUNDAMENTALS (Screener.in primary, Yahoo quoteSummary fallback) ─────
    async def get_fundamentals(self, ticker: str) -> dict:
        """
        Fetch fundamental data — Screener.in first (free, reliable, real), then
        Yahoo quoteSummary (free, direct). The yfinance library fallback was
        removed: from this environment Yahoo's library endpoints return 429 and
        yfinance retries with backoff, which 429-storms and stalls batch screens.
        """
        # Try Screener.in first (free, no rate limiting)
        try:
            from services.screener_service import screener_service
            data = await screener_service.get_fundamentals(ticker)
            if data and (data.get("pe_ratio") or data.get("roe")):
                return data
        except Exception as e:
            logger.warning(f"Screener.in failed for {ticker}: {e}")

        # Try direct Yahoo quoteSummary endpoint (free, direct)
        try:
            data = await self.get_yahoo_quote_summary(ticker)
            if data and (data.get("pe_ratio") or data.get("roe")):
                return data
        except Exception as e:
            logger.warning(f"Yahoo quoteSummary failed for {ticker}: {e}")

        return {}


# ── QUANT FACTOR COMPUTATION (single stock) ──────────────────────

def compute_quant_factors(df: pd.DataFrame, fundamentals: dict) -> dict:
    """
    Compute quant factor scores for a single stock from price history + fundamentals.
    Returns percentile-style scores (0-100) for each factor.
    """
    factors = {}
    close = df["close"]

    # ── MOMENTUM ──────────────────────────────────────────────────
    if len(close) >= 252:
        factors["momentum_12_1"] = round(float((close.iloc[-22] / close.iloc[-252] - 1) * 100), 2)
    if len(close) >= 126:
        factors["momentum_6_1"] = round(float((close.iloc[-22] / close.iloc[-126] - 1) * 100), 2)
    if len(close) >= 63:
        factors["momentum_3_1"] = round(float((close.iloc[-22] / close.iloc[-63] - 1) * 100), 2)
    if len(close) >= 21:
        factors["momentum_1m"] = round(float((close.iloc[-1] / close.iloc[-21] - 1) * 100), 2)

    # Composite momentum score (0-100 scale)
    mom_scores = []
    for k in ["momentum_12_1", "momentum_6_1", "momentum_3_1", "momentum_1m"]:
        if k in factors:
            # Map to 0-100: -50% = 0, 0% = 50, +50% = 100
            mom_scores.append(max(0, min(100, 50 + factors[k])))
    factors["momentum_score"] = round(np.mean(mom_scores), 1) if mom_scores else None

    # ── TECHNICALS ────────────────────────────────────────────────
    if len(close) >= 14:
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi_val = 100 - 100 / (1 + rs.iloc[-1])
        # Guard the degenerate windows: all gains -> loss is 0 -> rs is NaN -> RSI
        # should be 100 (not NaN, which would leak to the API); flat/insufficient -> 50.
        if pd.isna(rsi_val):
            rsi_val = 100.0 if (loss.iloc[-1] == 0 and gain.iloc[-1] > 0) else 50.0
        factors["rsi_14"] = round(float(rsi_val), 1)

    if len(close) >= 50:
        factors["sma_50"] = round(float(close.rolling(50).mean().iloc[-1]), 2)
    if len(close) >= 200:
        factors["sma_200"] = round(float(close.rolling(200).mean().iloc[-1]), 2)

    if len(close) >= 20:
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        factors["bb_upper"] = round(float(sma20.iloc[-1] + 2 * std20.iloc[-1]), 2)
        factors["bb_lower"] = round(float(sma20.iloc[-1] - 2 * std20.iloc[-1]), 2)
        factors["bb_position"] = round(float((close.iloc[-1] - factors["bb_lower"]) / (factors["bb_upper"] - factors["bb_lower"]) * 100), 1) if factors["bb_upper"] != factors["bb_lower"] else 50

    # ── VOLATILITY ────────────────────────────────────────────────
    if len(close) >= 60:
        daily_rets = close.pct_change().dropna()
        factors["volatility_60d"] = round(float(daily_rets.tail(60).std() * np.sqrt(252) * 100), 2)
        factors["volatility_252d"] = round(float(daily_rets.std() * np.sqrt(252) * 100), 2)

    # ── TREND ─────────────────────────────────────────────────────
    if "sma_50" in factors and "sma_200" in factors:
        factors["golden_cross"] = factors["sma_50"] > factors["sma_200"]
        factors["sma_spread_pct"] = round(float((factors["sma_50"] - factors["sma_200"]) / factors["sma_200"] * 100), 2)

    if len(close) >= 2:
        factors["return_1d"] = round(float((close.iloc[-1] / close.iloc[-2] - 1) * 100), 2)
    if len(close) >= 5:
        factors["return_5d"] = round(float((close.iloc[-1] / close.iloc[-5] - 1) * 100), 2)
    if len(close) >= 21:
        factors["return_1m"] = round(float((close.iloc[-1] / close.iloc[-21] - 1) * 100), 2)

    # ── QUALITY (from fundamentals) ───────────────────────────────
    quality_components = []
    roe = fundamentals.get("roe")
    if roe is not None:
        factors["roe"] = round(float(roe), 2)
        quality_components.append(max(0, min(100, roe * 2.5)))  # 40% ROE = 100

    gm = fundamentals.get("gross_margin")
    if gm is not None:
        factors["gross_margin"] = round(float(gm), 2)
        quality_components.append(max(0, min(100, gm)))

    em = fundamentals.get("ebitda_margin")
    if em is not None:
        factors["ebitda_margin"] = round(float(em), 2)
        quality_components.append(max(0, min(100, em * 2)))

    nm = fundamentals.get("net_margin")
    if nm is not None:
        factors["net_margin"] = round(float(nm), 2)
        quality_components.append(max(0, min(100, nm * 3)))

    de = fundamentals.get("debt_equity")
    if de is not None:
        factors["debt_equity"] = round(float(de), 2)
        quality_components.append(max(0, min(100, 100 - de * 2)))

    factors["quality_score"] = round(np.mean(quality_components), 1) if quality_components else None

    # ── VALUE (from fundamentals) ─────────────────────────────────
    value_components = []
    pe = fundamentals.get("pe_ratio")
    if pe is not None and pe > 0:
        factors["pe_ratio"] = round(float(pe), 2)
        value_components.append(max(0, min(100, 100 - (pe - 10) * 2)))  # PE 10=80, PE 50=0

    pb = fundamentals.get("pb_ratio")
    if pb is not None and pb > 0:
        factors["pb_ratio"] = round(float(pb), 2)
        value_components.append(max(0, min(100, 100 - (pb - 1) * 5)))  # PB 1=95, PB 20=0

    ev = fundamentals.get("ev_ebitda")
    if ev is not None and ev > 0:
        factors["ev_ebitda"] = round(float(ev), 2)
        value_components.append(max(0, min(100, 100 - (ev - 5) * 3)))  # EV/EBITDA 5=85, 35=0

    ps = fundamentals.get("ps_ratio")
    if ps is not None and ps > 0:
        factors["ps_ratio"] = round(float(ps), 2)
        value_components.append(max(0, min(100, 100 - (ps - 1) * 8)))

    factors["value_score"] = round(np.mean(value_components), 1) if value_components else None

    # ── GROWTH (from fundamentals) ────────────────────────────────
    growth_components = []
    rg = fundamentals.get("revenue_growth")
    if rg is not None:
        factors["revenue_growth"] = round(float(rg), 2)
        growth_components.append(max(0, min(100, 50 + rg * 2)))

    eg = fundamentals.get("earnings_growth")
    if eg is not None:
        factors["earnings_growth"] = round(float(eg), 2)
        growth_components.append(max(0, min(100, 50 + eg * 1.5)))

    eqg = fundamentals.get("earnings_qoq_growth")
    if eqg is not None:
        factors["earnings_qoq_growth"] = round(float(eqg), 2)
        growth_components.append(max(0, min(100, 50 + eqg * 2)))

    factors["growth_score"] = round(np.mean(growth_components), 1) if growth_components else None

    # ── COMPOSITE SCORE ───────────────────────────────────────────
    weights = {"momentum": 0.25, "quality": 0.25, "value": 0.20, "growth": 0.20}
    composite_parts = {}
    if factors.get("momentum_score") is not None:
        composite_parts["momentum"] = factors["momentum_score"] * weights["momentum"]
    if factors.get("quality_score") is not None:
        composite_parts["quality"] = factors["quality_score"] * weights["quality"]
    if factors.get("value_score") is not None:
        composite_parts["value"] = factors["value_score"] * weights["value"]
    if factors.get("growth_score") is not None:
        composite_parts["growth"] = factors["growth_score"] * weights["growth"]

    if composite_parts:
        total_weight = sum(weights[k] for k in composite_parts)
        factors["composite_score"] = round(sum(composite_parts.values()) / total_weight, 1)
    else:
        factors["composite_score"] = None

    return factors


fast_data_service = FastDataService()
