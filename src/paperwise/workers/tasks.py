from celery.utils.log import get_task_logger

from paperwise.application.interfaces import DocumentRepository, LLMProvider
from paperwise.application.services.file_relocation import move_blob_to_processed
from paperwise.application.services.history import (
    build_file_moved_history_event,
    build_processing_completed_history_event,
    build_processing_failed_history_event,
)
from paperwise.application.services.llm_preferences import (
    LLM_TASK_METADATA,
    LLM_TASK_OCR,
    get_normalized_llm_preferences,
)
from paperwise.application.services.llm_provider_factory import (
    resolve_llm_provider_from_preferences as resolve_configured_llm_provider,
)
from paperwise.application.services.llm_parsing import parse_with_llm
from paperwise.application.services.parsing import parse_document_blob
from paperwise.application.services.chunk_indexing import index_document_chunks
from paperwise.domain.models import DocumentStatus, HistoryActorType
from paperwise.infrastructure.config import get_settings
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


def _build_llm_provider() -> LLMProvider | None:
    return None


def _resolve_ocr_provider_for_owner(repository: DocumentRepository, owner_id: str) -> str:
    preference = repository.get_user_preference(owner_id)
    preferences = dict(preference.preferences) if preference is not None else {}
    normalized_llm = get_normalized_llm_preferences(preferences)
    if normalized_llm["llm_connections"]:
        ocr_route = normalized_llm["llm_routing"]["ocr"]
        if ocr_route["engine"] == "tesseract":
            return "tesseract"
        return "llm_separate"
    provider_name = str(preferences.get("ocr_provider", "llm")).strip().lower()
    if provider_name in {"tesseract", "llm", "llm_separate"}:
        return provider_name
    return "llm"


def _resolve_ocr_auto_switch_for_owner(repository: DocumentRepository, owner_id: str) -> bool:
    preference = repository.get_user_preference(owner_id)
    preferences = dict(preference.preferences) if preference is not None else {}
    raw = preferences.get("ocr_auto_switch", False)
    if isinstance(raw, bool):
        return raw
    normalized = str(raw).strip().lower()
    return normalized in {"true", "1", "on", "yes"}


def _resolve_llm_provider_from_preferences(
    *,
    preferences: dict[str, str],
    provider_override: LLMProvider | None,
    task: str = LLM_TASK_METADATA,
) -> LLMProvider:
    return resolve_configured_llm_provider(
        preferences=preferences,
        provider_override=provider_override,
        task=task,
        missing_provider_detail=f"missing provider setting for task: {task}",
        missing_api_key_detail=f"missing API key setting for task: {task}",
        missing_base_url_detail=f"missing base URL setting for task: {task}",
        error_factory=RuntimeError,
    )


def _resolve_metadata_llm_provider_for_owner(
    repository: DocumentRepository,
    owner_id: str,
    provider_override: LLMProvider | None,
) -> LLMProvider:
    preference = repository.get_user_preference(owner_id)
    preferences = dict(preference.preferences) if preference is not None else {}
    return _resolve_llm_provider_from_preferences(
        preferences=preferences,
        provider_override=provider_override,
        task=LLM_TASK_METADATA,
    )


def _resolve_ocr_llm_provider_for_owner(
    repository: DocumentRepository,
    owner_id: str,
    provider_override: LLMProvider | None,
    ocr_provider: str,
) -> LLMProvider | None:
    if ocr_provider == "tesseract":
        return None
    preference = repository.get_user_preference(owner_id)
    preferences = dict(preference.preferences) if preference is not None else {}
    if ocr_provider == "llm_separate":
        return _resolve_llm_provider_from_preferences(
            preferences=preferences,
            provider_override=provider_override,
            task=LLM_TASK_OCR,
        )
    return _resolve_llm_provider_from_preferences(
        preferences=preferences,
        provider_override=provider_override,
        task=LLM_TASK_OCR,
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
    repository = _build_repository()
    provider_override = _build_llm_provider()
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

        ocr_provider = _resolve_ocr_provider_for_owner(repository, document.owner_id)
        ocr_auto_switch = _resolve_ocr_auto_switch_for_owner(repository, document.owner_id)
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
        parsed = parse_document_blob(
            document_id=document_id,
            blob_uri=active_blob_uri,
            content_type=content_type,
            ocr_provider=ocr_provider,
            llm_provider=ocr_llm_provider,
            ocr_auto_switch=ocr_auto_switch,
        )
        repository.save_parse_result(parsed)
        chunk_count = index_document_chunks(
            repository=repository,
            document=document,
            parse_result=parsed,
        )
        logger.info("Indexed %d chunk(s) for document_id=%s", chunk_count, document.id)
        llm_result = parse_with_llm(
            document=document,
            parse_result=parsed,
            repository=repository,
            llm_provider=metadata_llm_provider,
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
                    parse_result=parsed,
                    llm_result=llm_result,
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
