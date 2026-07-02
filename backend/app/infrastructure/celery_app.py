from app.core.config import get_settings
from celery import Celery
from celery.schedules import crontab

settings = get_settings()


def create_celery_app() -> Celery:
    app = Celery(
        "memory_pulse",
        broker=settings.REDIS_BROKER_URL,
        backend=settings.REDIS_BROKER_URL,
    )

    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_routes={
            "app.infrastructure.tasks.price_tasks.*": {"queue": "prices"},
            "app.infrastructure.tasks.scraper_tasks.*": {"queue": "scrapers"},
        },
        result_expires=3600,
        task_max_retries=3,
        task_default_retry_delay=60,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        beat_schedule={
            "collect-prices-every-6h": {
                "task": "app.infrastructure.tasks.price_tasks.collect_all_prices",
                "schedule": crontab(minute=0, hour="*/6"),
                "options": {"queue": "prices"},
            },
            "generate-daily-summary": {
                "task": "app.infrastructure.tasks.price_tasks.generate_daily_summary",
                "schedule": crontab(minute=0, hour=1),
                "options": {"queue": "prices"},
            },
            "cleanup-old-records": {
                "task": "app.infrastructure.tasks.price_tasks.cleanup_old_records",
                "schedule": crontab(minute=0, hour=3, day_of_week=0),
                "options": {"queue": "prices"},
            },
        },
    )

    return app


celery_app = create_celery_app()
