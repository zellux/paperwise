from celery.utils.log import get_task_logger

from paperwise.application.interfaces import DocumentRepository, LLMProvider
from paperwise.application.services.file_relocation import move_blob_to_processed
from paperwise.application.services.history import (
    build_file_moved_history_event,
    build_processing_completed_history_event,
)
from paperwise.application.services.llm_parsing import parse_with_llm
from paperwise.application.services.parsing import parse_document_blob
from paperwise.domain.models import DocumentStatus, HistoryActorType
from paperwise.infrastructure.config import get_settings
from paperwise.infrastructure.llm.missing_openai_provider import MissingOpenAIProvider
from paperwise.infrastructure.llm.openai_llm_provider import OpenAILLMProvider
from paperwise.infrastructure.repositories.in_memory_document_repository import (
    InMemoryDocumentRepository,
)
from paperwise.infrastructure.repositories.postgres_document_repository import (
    PostgresDocumentRepository,
)
from paperwise.workers.celery_app import celery_app

logger = get_task_logger(__name__)
settings = get_settings()


def _build_repository() -> DocumentRepository:
    if settings.repository_backend.lower() == "postgres":
        return PostgresDocumentRepository(settings.postgres_url)
    return InMemoryDocumentRepository()


def _build_llm_provider() -> LLMProvider:
    if settings.openai_api_key:
        return OpenAILLMProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
        )
    return MissingOpenAIProvider()


@celery_app.task(name="paperwise.tasks.healthcheck")
def healthcheck_task() -> str:
    logger.info("worker healthcheck task executed")
    return "ok"


@celery_app.task(name="paperwise.tasks.ingest_document")
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


@celery_app.task(name="paperwise.tasks.parse_document")
def parse_document_task(
    document_id: str,
    blob_uri: str,
    filename: str,
    content_type: str,
) -> dict[str, str | int]:
    repository = _build_repository()
    llm_provider = _build_llm_provider()
    document = repository.get(document_id)
    if document is None:
        logger.error("parse task failed; document_id=%s not found", document_id)
        return {"document_id": document_id, "status": "not_found"}

    try:
        document.status = DocumentStatus.PROCESSING
        repository.save(document)

        parsed = parse_document_blob(document_id=document_id, blob_uri=blob_uri)
        repository.save_parse_result(parsed)
        parse_with_llm(
            document=document,
            parse_result=parsed,
            repository=repository,
            llm_provider=llm_provider,
            actor_type=HistoryActorType.SYSTEM,
            actor_id=None,
            history_source="worker.parse_document",
        )
        previous_blob_uri = document.blob_uri
        document.blob_uri = move_blob_to_processed(
            blob_uri=previous_blob_uri,
            object_store_root=settings.object_store_root,
            document_id=document.id,
            original_filename=document.filename,
            content_type=document.content_type,
            checksum_sha256=document.checksum_sha256,
            size_bytes=document.size_bytes,
        )
        previous_status = document.status.value
        document.status = DocumentStatus.READY
        repository.save(document)
        repository.append_history_events(
            [
                build_processing_completed_history_event(
                    document_id=document.id,
                    actor_type=HistoryActorType.SYSTEM,
                    actor_id=None,
                    source="worker.parse_document",
                    previous_status=previous_status,
                    current_status=document.status.value,
                )
            ]
        )
        file_move_event = build_file_moved_history_event(
            document_id=document.id,
            actor_type=HistoryActorType.SYSTEM,
            actor_id=None,
            source="worker.parse_document",
            from_blob_uri=previous_blob_uri,
            to_blob_uri=document.blob_uri,
        )
        if file_move_event is not None:
            repository.append_history_events([file_move_event])
    except Exception:
        logger.exception("analysis pipeline failed for document_id=%s", document_id)
        raise

    logger.info(
        "analysis complete document_id=%s filename=%s bytes=%d pages=%d content_type=%s",
        document_id,
        filename,
        parsed.size_bytes,
        parsed.page_count,
        content_type,
    )
    return {
        "document_id": document_id,
        "bytes": parsed.size_bytes,
        "parser": parsed.parser,
        "status": "ready",
    }
