from celery import Celery

from zapis.infrastructure.config import get_settings

settings = get_settings()

celery_app = Celery(
    "zapis",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.task_default_queue = "zapis-default"
celery_app.autodiscover_tasks(["zapis.workers"])

