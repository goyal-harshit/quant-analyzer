"""
Fast Data Service — Direct Yahoo Finance API (no yfinance library)
===================================================================
Bypasses the yfinance library's rate limiting by calling Yahoo Finance
API endpoints directly via httpx. Works reliably from Docker containers.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import httpx
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

YAHOO_BASE = "https://query1.finance.yahoo.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


class FastDataService:
    """
    Direct Yahoo Finance API calls — fast, reliable, no rate limiting.
    """

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=12.0, headers=HEADERS)

    async def _get(self, url: str, params: dict = None) -> Optional[dict]:
        try:
            resp = await self.client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning(f"Yahoo API error: {e}")
        return None

    # ── PRICE HISTORY ─────────────────────────────────────────────
    async def get_price_history(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """Fetch OHLCV history directly from Yahoo Finance chart API."""
        period_map = {"1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y"}
        range_val = period_map.get(period, "1y")

        data = await self._get(
            f"{YAHOO_BASE}/v8/finance/chart/{ticker}.NS",
            params={"interval": "1d", "range": range_val, "includePrePost": "false"}
        )
        if not data:
            # Try BSE
            data = await self._get(
                f"{YAHOO_BASE}/v8/finance/chart/{ticker}.BO",
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

    # ── LIVE QUOTE ────────────────────────────────────────────────
    async def get_quote(self, ticker: str) -> dict:
        """Fetch current quote from Yahoo Finance chart API (1d range)."""
        data = await self._get(
            f"{YAHOO_BASE}/v8/finance/chart/{ticker}.NS",
            params={"interval": "1d", "range": "5d", "includePrePost": "false"}
        )
        if not data or not data.get("chart", {}).get("result"):
            return {}

        meta = data["chart"]["result"][0]["meta"]
        return {
            "ticker": ticker,
            "name": meta.get("shortName", meta.get("longName", ticker)),
            "price": meta.get("regularMarketPrice", 0),
            "prev_close": meta.get("chartPreviousClose", meta.get("previousClose", 0)),
            "open": meta.get("regularMarketDayOpen", 0),
            "day_high": meta.get("regularMarketDayHigh", 0),
            "day_low": meta.get("regularMarketDayLow", 0),
            "volume": meta.get("regularMarketVolume", 0),
            "market_cap": meta.get("marketCap", 0),
            "fifty_two_week_high": meta.get("fiftyTwoWeekHigh", 0),
            "fifty_two_week_low": meta.get("fiftyTwoWeekLow", 0),
            "fifty_day_avg": meta.get("fiftyDayAverage", 0),
            "two_hundred_day_avg": meta.get("twoHundredDayAverage", 0),
            "year_change_pct": meta.get("yearChange", 0) * 100,
            "currency": meta.get("currency", "INR"),
            "exchange": meta.get("exchangeName", "NSE"),
        }

    # ── FUNDAMENTALS (Screener.in primary, yfinance fallback) ─────
    async def get_fundamentals(self, ticker: str) -> dict:
        """
        Fetch fundamental data — Screener.in first (free, reliable),
        then yfinance as fallback (rate-limited).
        """
        # Try Screener.in first (free, no rate limiting)
        try:
            from services.screener_service import screener_service
            data = await screener_service.get_fundamentals(ticker)
            if data and (data.get("pe_ratio") or data.get("roe")):
                logger.info(f"Screener.in fundamentals OK for {ticker}")
                return data
        except Exception as e:
            logger.warning(f"Screener.in failed for {ticker}: {e}")

        # Fallback: yfinance (may be rate-limited)
        try:
            import yfinance as yf

            loop = asyncio.get_event_loop()

            def fetch():
                t = yf.Ticker(f"{ticker}.NS")
                try:
                    info = t.info
                    if info and "trailingPE" in info:
                        return info
                except Exception:
                    pass
                return {}

            info = await loop.run_in_executor(None, fetch)

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
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "peg_ratio": info.get("pegRatio"),
                "roe": _pct(info.get("returnOnEquity")),
                "roa": _pct(info.get("returnOnAssets")),
                "gross_margin": _pct(info.get("grossMargins")),
                "ebitda_margin": _pct(info.get("ebitdaMargins")),
                "net_margin": _pct(info.get("profitMargins")),
                "operating_margin": _pct(info.get("operatingMargins")),
                "revenue_growth": _pct(info.get("revenueGrowth")),
                "earnings_growth": _pct(info.get("earningsGrowth")),
                "debt_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "free_cashflow": info.get("freeCashflow"),
                "beta": info.get("beta"),
                "dividend_yield": _pct(info.get("dividendYield")),
                "market_cap": info.get("marketCap"),
                "enterprise_value": info.get("enterpriseValue"),
                "book_value": info.get("bookValue"),
            }
        except Exception as e:
            logger.warning(f"yfinance fundamentals failed for {ticker}: {e}")
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
        factors["rsi_14"] = round(float(100 - 100 / (1 + rs.iloc[-1])), 1)

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
