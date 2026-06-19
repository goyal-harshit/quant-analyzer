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

from routers import stocks, screener, portfolio, backtest, macro, ai, dashboard, news, earnings, quant_lab, strategy_builder, watchlists, alerts, auth, insight
from models.database import init_db, get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    yield
    logger.info("👋 QuantAI Backend shutting down")


app = FastAPI(
    title="QuantAI API",
    description="India-First Quantitative Investment Analytics Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000")
origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
