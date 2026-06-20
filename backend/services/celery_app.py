"""Celery application for background tasks (data ingestion, etc.)"""

from celery import Celery
import os

celery_app = Celery(
    "quantai",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
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
    "warm-live-universe-every-30-min": {
        "task": "services.tasks.warm_live_universe_task",
        "schedule": crontab(minute="*/30"),
    },
}
