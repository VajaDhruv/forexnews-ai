from celery import Celery
from app.config import settings

celery_app = Celery(
    "forexnews",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.services.news_ingestion",
        "app.services.forex_data",
        "app.services.prediction_engine",
    ]
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=100,
    result_expires=3600,
    result_extended=True,
    beat_schedule={
        "retrain-models": {
            "task": "app.services.ml_tasks.retrain_models",
            "schedule": settings.RETRAIN_INTERVAL_HOURS * 3600,
        },
        "cleanup-old-data": {
            "task": "app.services.maintenance_tasks.cleanup_old_data",
            "schedule": 3600,  # Every hour
        },
        "update-model-performance": {
            "task": "app.services.ml_tasks.update_model_performance",
            "schedule": 3600,  # Every hour
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks()


@celery_app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")