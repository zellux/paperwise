from celery import Celery

from paperwise.infrastructure.config import get_settings

settings = get_settings()

celery_app = Celery(
    "paperwise",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.task_default_queue = "paperwise-default"
celery_app.autodiscover_tasks(["paperwise.workers"])

