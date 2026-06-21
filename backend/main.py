"""
QuantAI Backend — FastAPI Application
India-First Quantitative Investment Platform
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import logging
import os
from datetime import datetime, timezone

# ── Domain modules (PROJECT_PLAN §4: each domain under modules/<name>/) ──
from modules.stocks import router as stocks
from modules.screener import router as screener
from modules.portfolio import router as portfolio
from modules.backtest import router as backtest
from modules.macro import router as macro
from modules.ai import router as ai
from modules.dashboard import router as dashboard
from modules.news import router as news
from modules.earnings import router as earnings
from modules.quant_lab import router as quant_lab
from modules.strategy_builder import router as strategy_builder
from modules.watchlists import router as watchlists
from modules.alerts import router as alerts
from modules.auth import router as auth
from modules.insight import router as insight
from modules.mutual_funds import router as mutual_funds_router
from modules.ipo import router as ipo_router
from modules.simulator import router as simulator
from modules.compare import router as compare
from modules.sectors import router as sectors
# Import module models so init_db()'s create_all registers their tables.
from modules.mutual_funds import models as _mf_models  # noqa: F401
from modules.ipo import models as _ipo_models  # noqa: F401
from modules.simulator import models as _sim_models  # noqa: F401
from models.database import init_db, get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _warm_universe():
    """Background warm-up: pre-cache universe fundamentals + factor scores so the
    screener and dashboard are fast on first hit (avoids 50 cold screener.in scrapes
    on the request path). Guarded by a Redis flag so frequent dev reloads don't re-run it."""
    try:
        from services.data_service import data_service, _get_redis
        r = await _get_redis()
        if r:
            try:
                if await r.get("warm:universe"):
                    return
                await r.setex("warm:universe", 600, "1")
            except Exception:
                pass
        logger.info("🔥 Warming universe + sector caches…")
        # Warm the composite universe (dashboard rankings + sector core). We do NOT
        # pre-storm 50 fundamentals here — those sources (Screener.in / Yahoo
        # quoteSummary) are frequently blocked from this host and the retry storm
        # saturates the single worker, stalling every other request. Fundamentals
        # fill in lazily/best-effort instead.
        await data_service.get_universe_overview()
        try:
            from modules.sectors import service as sectors_service
            await sectors_service.get_sectors()
        except Exception as e:
            logger.warning(f"Sector cache warm failed: {e}")
        try:
            # Pre-cache the full mfapi scheme list so the first MF search is instant.
            from modules.mutual_funds.service import _all_schemes
            await _all_schemes()
        except Exception as e:
            logger.warning(f"MF scheme list warm failed: {e}")
        logger.info("✅ Universe + sector caches warmed")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Universe warm-up failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info("🚀 QuantAI Backend starting up…")
    try:
        await init_db()
        logger.info("✅ Database initialised")
    except Exception as e:
        logger.warning(f"⚠️  Database unavailable — running in seed-data-only mode: {e}")
    # Eager Redis connect — absorb the 2s timeout at startup, not on first request
    try:
        from services.data_service import _get_redis
        r = await _get_redis()
        if r:
            logger.info("✅ Redis connected")
        else:
            logger.info("ℹ️  Redis unavailable — running without cache")
    except Exception:
        logger.info("ℹ️  Redis connection failed — running without cache")
    # Kick off universe cache warm-up in the background (non-blocking).
    asyncio.create_task(_warm_universe())
    yield
    logger.info("👋 QuantAI Backend shutting down")


app = FastAPI(
    title="QuantAI API",
    description="India-First Quantitative Investment Analytics Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ── RATE LIMITING ─────────────────────────────────────────────────
# Global default limits + per-route limits (login, AI). Guards against
# resource abuse on the public compute/LLM endpoints and login brute-force.
from services.rate_limit import install_rate_limiting  # noqa: E402
install_rate_limiting(app)

# ── CORS ─────────────────────────────────────────────────────────
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://goyal-harshit\.github\.io",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── GLOBAL EXCEPTION HANDLER ──────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# ── ROUTERS ──────────────────────────────────────────────────────
app.include_router(stocks.router,    prefix="/api/v1/stocks",    tags=["Stocks"])
app.include_router(screener.router,  prefix="/api/v1/screener",  tags=["Screener"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])
app.include_router(backtest.router,  prefix="/api/v1/backtest",  tags=["Backtest"])
app.include_router(macro.router,     prefix="/api/v1/macro",     tags=["Macro"])
app.include_router(ai.router,        prefix="/api/v1/ai",        tags=["AI"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(news.router,      prefix="/api/v1/news",      tags=["News"])
app.include_router(earnings.router,  prefix="/api/v1/earnings",  tags=["Earnings"])
app.include_router(quant_lab.router, prefix="/api/v1/quant-lab", tags=["Quant Lab"])
app.include_router(strategy_builder.router, prefix="/api/v1/strategy-builder", tags=["Strategy Builder"])
app.include_router(watchlists.router, prefix="/api/v1/watchlists", tags=["Watchlists"])
app.include_router(alerts.router,    prefix="/api/v1/alerts",    tags=["Alerts"])
app.include_router(auth.router,      prefix="/api/v1/auth",      tags=["Auth"])
app.include_router(insight.router,   prefix="/api/v1/insight",   tags=["Insight"])
app.include_router(mutual_funds_router.router, prefix="/api/v1/mf",  tags=["Mutual Funds"])
app.include_router(ipo_router.router,          prefix="/api/v1/ipo", tags=["IPO"])
app.include_router(simulator.router,           prefix="/api/v1/simulator", tags=["Simulator"])
app.include_router(compare.router,             prefix="/api/v1/compare", tags=["Compare"])
app.include_router(sectors.router,             prefix="/api/v1/sectors", tags=["Sectors"])


@app.get("/")
async def root():
    return {
        "app": "QuantAI",
        "version": "1.0.0",
        "description": "India-First Quantitative Investment Analytics",
        "docs": "/docs",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
async def health(db = Depends(get_db)):
    from sqlalchemy import text
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.warning(f"Healthcheck: DB failed: {e}")

    redis_ok = False
    try:
        from services.cache_service import cache
        redis_ok = await cache.health()
    except Exception as e:
        logger.warning(f"Healthcheck: Redis failed: {e}")

    return {
        "status": "healthy" if (db_ok and redis_ok) else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
