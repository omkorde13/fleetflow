from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "fleetflow",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

celery_app.conf.beat_schedule = {
    "cleanup-expired-tokens": {
        "task": "app.workers.tasks.cleanup_expired_tokens",
        "schedule": crontab(minute=0),  # every hour
    },
    "generate-daily-report": {
        "task": "app.workers.tasks.generate_daily_report",
        "schedule": crontab(hour=0, minute=0),  # midnight
    },
    "update-driver-ratings": {
        "task": "app.workers.tasks.update_driver_ratings",
        "schedule": crontab(minute="*/30"),  # every 30 minutes
    },
}
