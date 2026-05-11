from celery.utils.log import get_task_logger

from paperwise.application.interfaces import DocumentRepository, LLMProvider
from paperwise.application.services.history import (
    build_processing_failed_history_event,
)
from paperwise.application.services.document_pipeline import process_document
from paperwise.application.services.llm_preferences import (
    LLM_TASK_METADATA,
    LLM_TASK_OCR,
)
from paperwise.application.services.llm_provider_factory import (
    resolve_llm_provider_for_user,
    resolve_ocr_llm_provider_for_user,
)
from paperwise.application.services.ocr_preferences import (
    resolve_owner_ocr_auto_switch,
    resolve_owner_ocr_provider,
)
from paperwise.domain.models import DocumentStatus, HistoryActorType
from paperwise.infrastructure.config import get_settings
from paperwise.infrastructure.factories import build_document_repository, build_llm_provider
from paperwise.workers.celery_app import celery_app

logger = get_task_logger(__name__)
settings = get_settings()


def _resolve_metadata_llm_provider_for_owner(
    repository: DocumentRepository,
    owner_id: str,
    provider_override: LLMProvider | None,
) -> LLMProvider:
    return resolve_llm_provider_for_user(
        repository=repository,
        user_id=owner_id,
        provider_override=provider_override,
        task=LLM_TASK_METADATA,
        missing_provider_detail=f"missing provider setting for task: {LLM_TASK_METADATA}",
        missing_api_key_detail=f"missing API key setting for task: {LLM_TASK_METADATA}",
        missing_base_url_detail=f"missing base URL setting for task: {LLM_TASK_METADATA}",
        error_factory=RuntimeError,
    )


def _resolve_ocr_llm_provider_for_owner(
    repository: DocumentRepository,
    owner_id: str,
    provider_override: LLMProvider | None,
    ocr_provider: str,
) -> LLMProvider | None:
    return resolve_ocr_llm_provider_for_user(
        repository=repository,
        user_id=owner_id,
        provider_override=provider_override,
        ocr_provider=ocr_provider,
        missing_provider_detail=f"missing provider setting for task: {LLM_TASK_OCR}",
        missing_api_key_detail=f"missing API key setting for task: {LLM_TASK_OCR}",
        missing_base_url_detail=f"missing base URL setting for task: {LLM_TASK_OCR}",
        error_factory=RuntimeError,
    )


def _resolve_active_blob_uri(*, document, queued_blob_uri: str) -> str:
    current_blob_uri = str(document.blob_uri or "").strip()
    normalized_queued_blob_uri = str(queued_blob_uri or "").strip()
    if current_blob_uri and current_blob_uri != normalized_queued_blob_uri:
        logger.info(
            "parse task using current blob_uri for document_id=%s queued=%s current=%s",
            document.id,
            normalized_queued_blob_uri,
            current_blob_uri,
        )
    return current_blob_uri or normalized_queued_blob_uri


def _is_already_ready_document(
    *,
    document,
    repository: DocumentRepository,
) -> bool:
    if document.status != DocumentStatus.READY:
        return False
    if not str(document.blob_uri or "").startswith("processed/"):
        return False
    return repository.get_parse_result(document.id) is not None


def _format_processing_failure_message(exc: Exception) -> str:
    message = str(exc).strip() or type(exc).__name__
    normalized = message.lower()
    if "llm ocr failed" in normalized and "404" in normalized and "openrouter" in normalized:
        return (
            "LLM OCR failed because OpenRouter returned HTTP 404. "
            "Check that the OCR route uses a valid OpenRouter model slug and a vision-capable model, "
            "or switch OCR to Gemini, OpenAI, or local Tesseract. "
            f"Raw error: {message}"
        )
    if "llm ocr failed" in normalized and "404" in normalized:
        return (
            "LLM OCR failed because the provider returned HTTP 404. "
            "Check that the OCR route uses a valid model name and base URL, and that the model supports images. "
            f"Raw error: {message}"
        )
    if "llm ocr failed" in normalized and ("image" in normalized or "vision" in normalized):
        return (
            "LLM OCR failed while sending an image to the configured provider. "
            "Check that the OCR model supports vision input, or switch OCR to local Tesseract. "
            f"Raw error: {message}"
        )
    return message


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
    repository = build_document_repository(settings)
    provider_override = build_llm_provider(settings)
    document = repository.get(document_id)
    if document is None:
        logger.error("parse task failed; document_id=%s not found", document_id)
        return {"document_id": document_id, "status": "not_found"}

    active_blob_uri = _resolve_active_blob_uri(document=document, queued_blob_uri=blob_uri)
    existing_parse_result = repository.get_parse_result(document_id)
    if _is_already_ready_document(document=document, repository=repository):
        logger.info(
            "parse task skipped for already-ready document_id=%s blob_uri=%s",
            document_id,
            active_blob_uri,
        )
        return {
            "document_id": document_id,
            "bytes": document.size_bytes,
            "parser": existing_parse_result.parser if existing_parse_result is not None else "unknown",
            "status": document.status.value,
        }

    try:
        document.status = DocumentStatus.PROCESSING
        repository.save(document)

        ocr_provider = resolve_owner_ocr_provider(repository, document.owner_id)
        ocr_auto_switch = resolve_owner_ocr_auto_switch(repository, document.owner_id)
        metadata_llm_provider = _resolve_metadata_llm_provider_for_owner(
            repository=repository,
            owner_id=document.owner_id,
            provider_override=provider_override,
        )
        ocr_llm_provider = _resolve_ocr_llm_provider_for_owner(
            repository=repository,
            owner_id=document.owner_id,
            provider_override=provider_override,
            ocr_provider=ocr_provider,
        )
        pipeline_result = process_document(
            document=document,
            repository=repository,
            object_store_root=settings.object_store_root,
            metadata_llm_provider=metadata_llm_provider,
            ocr_provider=ocr_provider,
            ocr_llm_provider=ocr_llm_provider,
            ocr_auto_switch=ocr_auto_switch,
            actor_type=HistoryActorType.SYSTEM,
            actor_id=None,
            history_source="worker.parse_document",
            parse_blob_uri=active_blob_uri,
            content_type=content_type,
        )
        logger.info("Indexed %d chunk(s) for document_id=%s", pipeline_result.indexed_chunk_count, document.id)
    except Exception as exc:
        logger.exception("analysis pipeline failed for document_id=%s", document_id)
        previous_status = document.status.value
        document.status = DocumentStatus.FAILED
        repository.save(document)
        repository.append_history_events(
            [
                build_processing_failed_history_event(
                    document_id=document.id,
                    actor_type=HistoryActorType.SYSTEM,
                    actor_id=None,
                    source="worker.parse_document",
                    previous_status=previous_status,
                    current_status=document.status.value,
                    error_message=_format_processing_failure_message(exc),
                    error_type=type(exc).__name__,
                )
            ]
        )
        raise

    logger.info(
        "analysis complete document_id=%s filename=%s bytes=%d pages=%d content_type=%s",
        document_id,
        filename,
        pipeline_result.parse_result.size_bytes,
        pipeline_result.parse_result.page_count,
        content_type,
    )
    return {
        "document_id": document_id,
        "bytes": pipeline_result.parse_result.size_bytes,
        "parser": pipeline_result.parse_result.parser,
        "status": "ready",
    }
