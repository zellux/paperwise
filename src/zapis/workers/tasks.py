from celery.utils.log import get_task_logger

from zapis.workers.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="zapis.tasks.healthcheck")
def healthcheck_task() -> str:
    logger.info("worker healthcheck task executed")
    return "ok"

