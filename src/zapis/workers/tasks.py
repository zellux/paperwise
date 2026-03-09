from celery.utils.log import get_task_logger

from zapis.workers.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="zapis.tasks.healthcheck")
def healthcheck_task() -> str:
    logger.info("worker healthcheck task executed")
    return "ok"


@celery_app.task(name="zapis.tasks.ingest_document")
def ingest_document_task(document_id: str) -> str:
    logger.info("ingestion task queued for document_id=%s", document_id)
    return document_id
