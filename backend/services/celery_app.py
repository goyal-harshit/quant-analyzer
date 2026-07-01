"""Celery application for background tasks (data ingestion, etc.)"""

from celery import Celery
import os

# Use SEPARATE Redis logical DBs for the Celery broker (/1) and result backend
# (/2) so they don't collide with the application cache (which uses /0).
_redis_base = os.getenv("REDIS_URL", "redis://localhost:6379/0").rsplit("/", 1)[0]

celery_app = Celery(
    "quantai",
    broker=os.getenv("CELERY_BROKER_URL", f"{_redis_base}/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", f"{_redis_base}/2"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=300,
)

celery_app.autodiscover_tasks(["services"])

from celery.schedules import crontab

# Beat schedule intentionally minimal.
#
# The previous schedule did more harm than good in this environment:
#  - ingest-prices/refresh-fundamentals used yfinance, which is 429-blocked here
#    (constant rate-limit storms, no useful data).
#  - refresh-daily-seed-cache wrote SEED values into the `fund_`/`q_` caches with
#    a 24h TTL, masking the live fundamentals served by the API.
#
# Freshness is now handled by: the backend startup warm-up (live NIFTY-50
# fundamentals + factor scores), on-demand live fetches (Yahoo v8 chart +
# screener.in), and per-key cache TTLs. The only periodic job is a light LIVE
# warm of the liquid universe to keep the dashboard/screener fast.
celery_app.conf.beat_schedule = {
    # Warm the liquid universe (live NIFTY-50 fundamentals + factor signals) every
    # 15 minutes — matches the "signals updated every 15 minutes" product promise.
    # The reliability layer (circuit breakers + rate limiters) guards the sources.
    "warm-live-universe-every-15-min": {
        "task": "services.tasks.warm_live_universe_task",
        "schedule": crontab(minute="*/15"),
    },
    # Ingest-then-serve: refresh the market_* store from the guarded LIVE chain so
    # the API serves fresh quotes/fundamentals/history straight from the DB. Safe
    # to run periodically now that every source is behind a circuit breaker.
    "refresh-market-store-every-15-min": {
        "task": "services.tasks.refresh_market_store_task",
        "schedule": crontab(minute="*/15"),
    },
}
