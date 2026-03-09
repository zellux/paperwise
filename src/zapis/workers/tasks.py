from celery.utils.log import get_task_logger

from zapis.workers.celery_app import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="zapis.tasks.healthcheck")
def healthcheck_task() -> str:
    logger.info("worker healthcheck task executed")
    return "ok"


@celery_app.task(name="zapis.tasks.ingest_document")
def ingest_document_task(
    document_id: str,
    blob_uri: str,
    filename: str,
    content_type: str,
) -> dict[str, str]:
    logger.info(
        "ingestion task started for document_id=%s blob_uri=%s",
        document_id,
        blob_uri,
    )
    parse_document_task.delay(
        document_id=document_id,
        blob_uri=blob_uri,
        filename=filename,
        content_type=content_type,
    )
    return {"document_id": document_id, "status": "processing"}


@celery_app.task(name="zapis.tasks.parse_document")
def parse_document_task(
    document_id: str,
    blob_uri: str,
    filename: str,
    content_type: str,
) -> dict[str, str | int]:
    # Placeholder parser: verifies stored content is readable and identifies PDF signature.
    from pathlib import Path
    from urllib.parse import unquote, urlparse

    parsed = urlparse(blob_uri)
    path = Path(unquote(parsed.path))
    raw = path.read_bytes()
    is_pdf = raw.startswith(b"%PDF")
    logger.info(
        "parsed document_id=%s filename=%s bytes=%d pdf=%s content_type=%s",
        document_id,
        filename,
        len(raw),
        is_pdf,
        content_type,
    )
    return {
        "document_id": document_id,
        "bytes": len(raw),
        "parser": "stub",
        "status": "parsed",
    }
    return document_id
