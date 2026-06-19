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

celery_app.conf.beat_schedule = {
    "ingest-prices-every-15-min": {
        "task": "services.tasks.ingest_prices_task",
        "schedule": crontab(minute="*/15", hour="9-15", day_of_week="1-5"),
        "args": (100,),
    },
    "compute-factors-nightly": {
        "task": "services.tasks.compute_factors_task",
        "schedule": crontab(minute="0", hour="22", day_of_week="1-5"),
        "args": (100,),
    },
    "refresh-fundamentals-weekly": {
        "task": "services.tasks.refresh_fundamentals_task",
        "schedule": crontab(minute="0", hour="6", day_of_week="0"),
        "args": (100,),
    },
    "refresh-daily-seed-cache": {
        "task": "services.tasks.refresh_daily_seed_cache_task",
        "schedule": crontab(minute="15", hour="*/6"),
    },
}
