"""Insight Agent — Parallel multi-source data dispatcher.
Fans out requests to independent "agents" (quote, fundamentals, history,
technicals, factors, news, AI) and merges results into a single response.
All agents run concurrently via asyncio.gather for minimum latency.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

from services.data_service import data_service
from services.factor_engine import FactorEngine
from services.seed_data import get_seed_quote, get_seed_fundamentals, DEFAULT_TICKERS
from services.cache_service import cache, TTL_PRICE_HISTORY, TTL_FACTOR_SCORES
from services.ai_service import ai_service

logger = logging.getLogger(__name__)
engine = FactorEngine()


class InsightAgent:
    def __init__(self):
        self._peer_cache = {}

    async def _agent_quote(self, ticker: str, refresh: bool = False) -> dict:
        """Agent 1: Fetch current quote — fastest path (seed data)."""
        try:
            q = await data_service.get_quote(ticker, refresh=refresh)
            if q and q.get("price"):
                return q
        except Exception:
            pass
        q = get_seed_quote(ticker)
        return q or {}

    async def _agent_fundamentals(self, ticker: str, refresh: bool = False) -> dict:
        """Agent 2: Fetch fundamentals — from cache or seed."""
        try:
            f = await data_service.get_fundamentals(ticker, refresh=refresh)
            if f:
                return f
        except Exception:
            pass
        f = get_seed_fundamentals(ticker)
        return f or {}

    async def _agent_history(self, ticker: str, period: str = "2y", refresh: bool = False) -> list:
        """Agent 3: Fetch price history."""
        try:
            df = await data_service.get_price_history(ticker, period=period, refresh=refresh)
            if df is not None and not df.empty:
                return [
                    {
                        "date": idx.strftime("%Y-%m-%d"),
                        "open": round(r["open"], 2),
                        "high": round(r["high"], 2),
                        "low": round(r["low"], 2),
                        "close": round(r["close"], 2),
                        "volume": int(r["volume"]),
                    }
                    for idx, r in df.iterrows()
                ]
        except Exception:
            pass
        return []

    async def _agent_technicals(self, ticker: str, refresh: bool = False) -> dict:
        """Agent 4: Compute technical indicators from cached/gathered history."""
        cache_key = f"tech_{ticker.upper()}"
        if not refresh:
            cached = await cache.get(cache_key)
            if cached:
                import json
                return json.loads(cached)

        df = await data_service.get_price_history(ticker, period="1y", refresh=refresh)
        if df is None or df.empty or len(df) < 50:
            return {}

        close = df["close"]
        bb = engine.bollinger_bands(close)

        result = {
            "rsi_14": round(engine.rsi(close), 2),
            "sma_50": round(float(close.rolling(50).mean().iloc[-1]), 2),
            "sma_200": round(float(close.rolling(200).mean().iloc[-1]), 2) if len(close) >= 200 else None,
            "bollinger": {
                "upper": round(float(bb["upper"].iloc[-1]), 2),
                "middle": round(float(bb["middle"].iloc[-1]), 2),
                "lower": round(float(bb["lower"].iloc[-1]), 2),
            },
            "atr_14": round(float(engine.atr(df["high"], df["low"], df["close"]).iloc[-1]), 2)
                if all(c in df.columns for c in ["high", "low", "close"]) else None,
        }

        import json
        await cache.set(cache_key, json.dumps(result), TTL_PRICE_HISTORY)
        return result

    async def _agent_factors(self, ticker: str, refresh: bool = False) -> dict:
        """Agent 5: Compute factor scores with cached fallback."""
        cache_key = f"fs_{ticker.upper()}"
        if not refresh:
            cached = await cache.get(cache_key)
            if cached:
                import json
                return json.loads(cached)

        prices_df = await data_service.get_price_history(ticker, period="2y", refresh=refresh)
        fundamentals = await data_service.get_fundamentals(ticker, refresh=refresh)
        close_prices = prices_df["close"] if prices_df is not None and not prices_df.empty else None

        result = {
            "ticker": ticker.upper(),
            "momentum": None,
            "quality": None,
            "value": None,
            "growth": None,
            "low_volatility": None,
            "composite": None,
        }

        if close_prices is None or len(close_prices) < 63:
            return result

        price_matrix = close_prices.to_frame(ticker).T if hasattr(close_prices, 'to_frame') else None
        fundamentals_df = None
        if fundamentals:
            fundamentals_df = pd.DataFrame([fundamentals]).set_index("ticker") if fundamentals.get("ticker") else None

        if price_matrix is not None:
            m_s = engine.compute_momentum_score(price_matrix)
            result["momentum"] = round(float(m_s.iloc[0]), 1) if not m_s.empty else None

            lv_s = engine.compute_low_vol_score(price_matrix)
            result["low_volatility"] = round(float(lv_s.iloc[0]), 1) if not lv_s.empty else None

        if fundamentals_df is not None:
            q_s = engine.compute_quality_score(fundamentals_df)
            result["quality"] = round(float(q_s.iloc[0]), 1) if not q_s.empty else None
            v_s = engine.compute_value_score(fundamentals_df)
            result["value"] = round(float(v_s.iloc[0]), 1) if not v_s.empty else None
            g_s = engine.compute_growth_score(fundamentals_df)
            result["growth"] = round(float(g_s.iloc[0]), 1) if not g_s.empty else None

        scores = {
            "momentum": result["momentum"],
            "quality": result["quality"],
            "value": result["value"],
            "growth": result["growth"],
            "low_volatility": result["low_volatility"],
        }
        valid = {k: v for k, v in scores.items() if v is not None}
        if valid:
            result["composite"] = round(sum(valid.values()) / len(valid), 1)

        import json
        await cache.set(cache_key, json.dumps(result), TTL_FACTOR_SCORES)
        return result

    async def _agent_peers(self, ticker: str, sector: Optional[str] = None) -> list:
        """Agent 6: Find peer companies in the same sector."""
        if not sector:
            sector = data_service._SECTOR_MAP.get(ticker.upper(), "Unknown")
        peers = [t for t in DEFAULT_TICKERS if data_service._SECTOR_MAP.get(t) == sector and t != ticker.upper()]
        return peers[:8]

    async def _agent_ai_summary(self, ticker: str, quote: dict, fundamentals: dict, factors: dict) -> Optional[str]:
        """Agent 7: Generate AI summary (runs in background, returns None if slow)."""
        try:
            stock_data = {
                "ticker": ticker, "name": fundamentals.get("name", ticker),
                "price": quote.get("price"), "change_pct": quote.get("change_pct"),
                "sector": fundamentals.get("sector"), "market_cap": fundamentals.get("market_cap"),
                "pe_ratio": fundamentals.get("pe_ratio"), "pb_ratio": fundamentals.get("pb_ratio"),
                "roe": fundamentals.get("roe"), "debt_equity": fundamentals.get("debt_to_equity"),
                "revenue_growth": fundamentals.get("revenue_growth"),
                "momentum_score": factors.get("momentum"), "quality_score": factors.get("quality"),
                "value_score": factors.get("value"), "growth_score": factors.get("growth"),
                "composite_score": factors.get("composite"),
            }
            report = await ai_service.generate_stock_report(stock_data, report_type="brief")
            return report
        except Exception as e:
            logger.warning(f"AI summary agent failed for {ticker}: {e}")
            return None

    async def get_insight(self, ticker: str, include_ai: bool = False, refresh: bool = False) -> dict:
        """Master coordinator — fans out to all agents in parallel, merges results."""
        t = ticker.upper()
        agents = {
            "quote": self._agent_quote(t, refresh=refresh),
            "fundamentals": self._agent_fundamentals(t, refresh=refresh),
            "history": self._agent_history(t, refresh=refresh),
            "technicals": self._agent_technicals(t, refresh=refresh),
            "factors": self._agent_factors(t, refresh=refresh),
        }

        results = await asyncio.gather(*agents.values(), return_exceptions=True)
        agent_names = list(agents.keys())
        agent_results = {}
        for name, res in zip(agent_names, results):
            if isinstance(res, Exception):
                logger.warning(f"Agent '{name}' failed for {t}: {res}")
                agent_results[name] = {} if name != "history" else []
            else:
                agent_results[name] = res

        quote = agent_results.get("quote", {})
        fundamentals = agent_results.get("fundamentals", {})
        factors = agent_results.get("factors", {})

        sector = fundamentals.get("sector") or data_service._SECTOR_MAP.get(t)
        peers = await self._agent_peers(t, sector)

        ai_summary = None
        if include_ai:
            ai_summary = await self._agent_ai_summary(t, quote, fundamentals, factors)

        change_pct = quote.get("change_pct")
        if change_pct is not None:
            try:
                change_pct = round(float(change_pct), 2)
            except (ValueError, TypeError):
                change_pct = None

        return {
            "ticker": t,
            "name": fundamentals.get("name") or quote.get("name") or t,
            "sector": sector,
            "industry": fundamentals.get("industry") or data_service._INDUSTRY_MAP.get(t),
            "quote": {
                "price": quote.get("price"),
                "change": quote.get("change"),
                "change_pct": change_pct,
                "volume": quote.get("volume"),
                "avg_volume": quote.get("avg_volume"),
                "day_high": quote.get("day_high"),
                "day_low": quote.get("day_low"),
                "fifty_two_week_high": quote.get("fifty_two_week_high"),
                "fifty_two_week_low": quote.get("fifty_two_week_low"),
                "market_cap": quote.get("market_cap") or fundamentals.get("market_cap"),
                "prev_close": quote.get("prev_close"),
                "source": quote.get("source"),
            },
            "fundamentals": {
                "pe_ratio": fundamentals.get("pe_ratio"),
                "pb_ratio": fundamentals.get("pb_ratio"),
                "ev_ebitda": fundamentals.get("ev_ebitda"),
                "ps_ratio": fundamentals.get("ps_ratio"),
                "roe": fundamentals.get("roe"),
                "roce": fundamentals.get("roce"),
                "roa": fundamentals.get("roa"),
                "debt_to_equity": fundamentals.get("debt_to_equity") or fundamentals.get("debt_equity"),
                "current_ratio": fundamentals.get("current_ratio"),
                "eps": fundamentals.get("eps"),
                "book_value": fundamentals.get("book_value"),
                "revenue": fundamentals.get("revenue"),
                "revenue_growth": fundamentals.get("revenue_growth"),
                "net_margin": fundamentals.get("net_margin"),
                "operating_margin": fundamentals.get("operating_margin"),
                "dividend_yield": fundamentals.get("dividend_yield"),
                "beta": fundamentals.get("beta"),
            },
            "technicals": agent_results.get("technicals", {}),
            "factors": factors,
            "history": agent_results.get("history", []),
            "peers": peers,
            "ai_summary": ai_summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


insight_agent = InsightAgent()
