"""
tasks.py — Celery background tasks for precomputation.
All heavy lifting (factor scores, technicals, data ingestion) runs here
so API endpoints serve cached/precomputed data instantly.
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor

from services.celery_app import celery_app
from models.database import AsyncSessionLocal
from services.ingestion_service import ingestion_service
from services.seed_data import DEFAULT_TICKERS, get_seed_fundamentals, get_seed_quote
from services.cache_service import cache, TTL_FACTOR_SCORES, TTL_PRICE_HISTORY

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run a coroutine to completion from a synchronous Celery worker.

    Celery prefork workers have no running loop, so a fresh loop per task is the
    safe default. Only if we're somehow already inside a running loop do we fall
    back to nest_asyncio.
    """
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None

    if running is not None:
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except ImportError:
            pass
        return running.run_until_complete(coro)

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


async def _precompute_single_factor(ticker: str) -> dict:
    """Compute and cache factor scores for one ticker."""
    from services.data_service import data_service
    from services.factor_engine import FactorEngine

    engine = FactorEngine()
    cache_key = f"fs_{ticker.upper()}"

    prices_df = await data_service.get_price_history(ticker, period="2y")
    fundamentals = await data_service.get_fundamentals(ticker)
    close = prices_df["close"] if prices_df is not None and not prices_df.empty else None

    result = {
        "ticker": ticker.upper(), "momentum": None, "quality": None,
        "value": None, "growth": None, "low_volatility": None, "composite": None,
    }
    if close is None or len(close) < 63:
        return result

    try:
        import pandas as pd
        pm = close.to_frame(ticker).T
        fd = pd.DataFrame([fundamentals]).set_index("ticker") if fundamentals and fundamentals.get("ticker") else None

        ms = engine.compute_momentum_score(pm)
        result["momentum"] = round(float(ms.iloc[0]), 1) if not ms.empty else None
        lv = engine.compute_low_vol_score(pm)
        result["low_volatility"] = round(float(lv.iloc[0]), 1) if not lv.empty else None

        if fd is not None:
            qs = engine.compute_quality_score(fd)
            result["quality"] = round(float(qs.iloc[0]), 1) if not qs.empty else None
            vs = engine.compute_value_score(fd)
            result["value"] = round(float(vs.iloc[0]), 1) if not vs.empty else None
            gs = engine.compute_growth_score(fd)
            result["growth"] = round(float(gs.iloc[0]), 1) if not gs.empty else None

        valid = {k: v for k, v in result.items() if v is not None and k != "ticker"}
        if valid:
            result["composite"] = round(sum(valid.values()) / len(valid), 1)
    except Exception as e:
        logger.warning(f"Factor precompute failed for {ticker}: {e}")

    await cache.set(cache_key, json.dumps(result), TTL_FACTOR_SCORES)
    return result


async def _precompute_single_technical(ticker: str) -> dict:
    """Compute and cache technical indicators for one ticker."""
    from services.data_service import data_service
    from services.factor_engine import FactorEngine

    engine = FactorEngine()
    cache_key = f"tech_{ticker.upper()}"

    df = await data_service.get_price_history(ticker, period="1y")
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

    await cache.set(cache_key, json.dumps(result), TTL_PRICE_HISTORY)
    return result


@celery_app.task
def precompute_all_factors_task():
    """Precompute factor scores for all DEFAULT_TICKERS and cache in Redis.
    Runs in parallel batches to minimise wall-clock time.
    """
    logger.info(f"Celery: precomputing factors for {len(DEFAULT_TICKERS)} tickers...")

    async def _run():
        sem = asyncio.Semaphore(20)
        async def _bound(t):
            async with sem:
                return await _precompute_single_factor(t)
        tasks = [_bound(t) for t in DEFAULT_TICKERS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ok = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Precomputed factors for {ok}/{len(DEFAULT_TICKERS)} tickers")

    run_async(_run())


@celery_app.task
def precompute_all_technicals_task():
    """Precompute technical indicators for all tickers and cache in Redis."""
    logger.info(f"Celery: precomputing technicals for {len(DEFAULT_TICKERS)} tickers...")

    async def _run():
        sem = asyncio.Semaphore(20)
        async def _bound(t):
            async with sem:
                return await _precompute_single_technical(t)
        tasks = [_bound(t) for t in DEFAULT_TICKERS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ok = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Precomputed technicals for {ok}/{len(DEFAULT_TICKERS)} tickers")

    run_async(_run())


@celery_app.task
def precompute_warm_cache_task():
    """Warm the Redis cache with seed data for all tickers.
    This ensures the first user request is fast (served from Redis).
    """
    logger.info("Celery: warming Redis cache with seed data...")

    async def _run():
        sem = asyncio.Semaphore(25)
        async def _warm(t):
            async with sem:
                try:
                    # Seed quotes only (short TTL). Do NOT write fund_ seed — it would
                    # mask the live fundamentals served by the API for 24h.
                    q = get_seed_quote(t)
                    if q:
                        await cache.set(f"q_{t}", json.dumps(q), 120)
                except Exception:
                    pass
        tasks = [_warm(t) for t in DEFAULT_TICKERS]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Redis warm with seed quotes for {len(DEFAULT_TICKERS)} tickers")

    run_async(_run())


@celery_app.task
def refresh_daily_seed_cache_task():
    """Refresh the Redis cache with fresh daily-varying seed data.
    Runs every 6 hours to keep quote/fundamentals data cycling.
    Uses date-seeded RNG so values change daily even without live API.
    """
    logger.info("Celery: refreshing daily seed cache...")

    async def _run():
        sem = asyncio.Semaphore(25)
        async def _refresh(t):
            async with sem:
                try:
                    # Quotes only, short TTL. Never write fund_ seed (masks live data).
                    q = get_seed_quote(t)
                    if q:
                        await cache.set(f"q_{t}", json.dumps(q), 120)
                except Exception as e:
                    logger.warning(f"Seed refresh failed for {t}: {e}")
        tasks = [_refresh(t) for t in list(DEFAULT_TICKERS)[:50]]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Daily seed quote cache refreshed for 50 tickers")

    run_async(_run())


@celery_app.task
def warm_live_universe_task():
    """Warm Redis with LIVE fundamentals + factor scores for the liquid NIFTY-50
    universe (screener.in + Yahoo v8 chart). No seed writes, no yfinance."""
    logger.info("Celery: warming LIVE universe cache (NIFTY 50)...")

    async def _run():
        from services.data_service import data_service, NIFTY_50_TICKERS, _gather_limited
        # Low concurrency — screener_service has a global rate gate; keep it gentle.
        await _gather_limited([data_service.get_fundamentals(t) for t in NIFTY_50_TICKERS], limit=3)
        await data_service.get_universe_overview(refresh=True)
        logger.info("Celery: live universe warm complete")

    run_async(_run())


@celery_app.task
def seed_database_task():
    """Initial seeding task to populate stock_master from local seeds."""
    logger.info("Celery: running seed_database_task...")
    async def _run():
        async with AsyncSessionLocal() as db:
            await ingestion_service.seed_stock_master(db)
    run_async(_run())


@celery_app.task
def ingest_prices_task(limit_tickers=50):
    """Ingest price history for top N tickers."""
    logger.info(f"Celery: running ingest_prices_task for top {limit_tickers} tickers...")
    async def _run():
        sem = asyncio.Semaphore(8)
        async def _ingest(s):
            async with sem:
                # Each coroutine gets its OWN session — AsyncSession is not safe
                # for concurrent use across coroutines.
                async with AsyncSessionLocal() as db:
                    try:
                        await ingestion_service.ingest_prices(db, s)
                        return True
                    except Exception as e:
                        logger.error(f"Failed to ingest price for {s}: {e}")
                        return False
        tasks = [_ingest(s) for s in DEFAULT_TICKERS[:limit_tickers]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        count = sum(1 for r in results if r is True)
        logger.info(f"Finished ingesting prices for {count} stocks.")
    from services.seed_data import DEFAULT_TICKERS
    run_async(_run())


@celery_app.task
def compute_factors_task(limit_tickers=50):
    """Nightly factor scores calculation — now parallel + Redis-cached."""
    logger.info(f"Celery: running compute_factors_task for top {limit_tickers} tickers...")
    async def _run():
        tickers = DEFAULT_TICKERS[:limit_tickers]
        sem = asyncio.Semaphore(15)
        async def _compute(t):
            async with sem:
                return await _precompute_single_factor(t)
        tasks = [_compute(t) for t in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ok = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Computed factors for {ok}/{len(tickers)} tickers.")
    from services.seed_data import DEFAULT_TICKERS
    run_async(_run())


@celery_app.task
def refresh_fundamentals_task(limit_tickers=50):
    """Refresh fundamental attributes from Yahoo/Screener.in — parallel."""
    logger.info(f"Celery: running refresh_fundamentals_task for top {limit_tickers} tickers...")
    async def _run():
        sem = asyncio.Semaphore(8)
        async def _refresh(s):
            async with sem:
                # Each coroutine gets its OWN session — AsyncSession is not safe
                # for concurrent use across coroutines.
                async with AsyncSessionLocal() as db:
                    try:
                        await ingestion_service.ingest_fundamentals(db, s)
                        return True
                    except Exception as e:
                        logger.error(f"Failed to ingest fundamentals for {s}: {e}")
                        return False
        tasks = [_refresh(s) for s in DEFAULT_TICKERS[:limit_tickers]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ok = sum(1 for r in results if r is True)
        logger.info(f"Refreshed fundamentals for {ok} stocks.")
    from services.seed_data import DEFAULT_TICKERS
    run_async(_run())
