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
from paperwise.infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from paperwise.infrastructure.llm.missing_openai_provider import MissingOpenAIProvider
from paperwise.infrastructure.llm.openai_llm_provider import OpenAILLMProvider
from paperwise.infrastructure.llm.simple_llm_provider import SimpleLLMProvider
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


def _resolve_ocr_provider_for_owner(repository: DocumentRepository, owner_id: str) -> str:
    preference = repository.get_user_preference(owner_id)
    preferences = dict(preference.preferences) if preference is not None else {}
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
    default_llm_provider: LLMProvider,
    provider_key: str = "llm_provider",
    model_key: str = "llm_model",
    base_url_key: str = "llm_base_url",
    api_key_key: str = "llm_api_key",
) -> LLMProvider:
    provider_name = str(preferences.get(provider_key, "")).strip().lower()

    # Preserve worker testability when a fake provider is injected.
    if not isinstance(
        default_llm_provider,
        (MissingOpenAIProvider, OpenAILLMProvider, GeminiLLMProvider, SimpleLLMProvider),
    ):
        return default_llm_provider

    if not provider_name:
        raise RuntimeError(f"missing provider setting: {provider_key}")

    configured_key = str(preferences.get(api_key_key, "")).strip()
    if not configured_key:
        raise RuntimeError(f"missing API key setting: {api_key_key}")

    ocr_image_detail = str(preferences.get("ocr_image_detail", "auto")).strip().lower()
    if ocr_image_detail not in {"auto", "low", "high"}:
        ocr_image_detail = "auto"

    if provider_name == "openai":
        model = str(preferences.get(model_key, "")).strip() or settings.openai_model
        base_url = str(preferences.get(base_url_key, "")).strip() or settings.openai_base_url
        return OpenAILLMProvider(
            api_key=configured_key,
            model=model,
            base_url=base_url,
            vision_image_detail=ocr_image_detail,
        )
    if provider_name == "gemini":
        model = str(preferences.get(model_key, "")).strip() or "gemini-2.0-flash"
        base_url = str(preferences.get(base_url_key, "")).strip() or "https://generativelanguage.googleapis.com/v1beta"
        return GeminiLLMProvider(
            api_key=configured_key,
            model=model,
            base_url=base_url,
        )
    if provider_name == "custom":
        base_url = str(preferences.get(base_url_key, "")).strip()
        if not base_url:
            raise RuntimeError(f"missing base URL setting: {base_url_key}")
        model = str(preferences.get(model_key, "")).strip() or settings.openai_model
        return OpenAILLMProvider(
            api_key=configured_key,
            model=model,
            base_url=base_url,
            vision_image_detail=ocr_image_detail,
        )
    raise RuntimeError(f"unsupported provider: {provider_name}")


def _resolve_metadata_llm_provider_for_owner(
    repository: DocumentRepository,
    owner_id: str,
    default_llm_provider: LLMProvider,
) -> LLMProvider:
    preference = repository.get_user_preference(owner_id)
    preferences = dict(preference.preferences) if preference is not None else {}
    return _resolve_llm_provider_from_preferences(
        preferences=preferences,
        default_llm_provider=default_llm_provider,
    )


def _resolve_ocr_llm_provider_for_owner(
    repository: DocumentRepository,
    owner_id: str,
    default_llm_provider: LLMProvider,
    ocr_provider: str,
) -> LLMProvider | None:
    if ocr_provider == "tesseract":
        return None
    preference = repository.get_user_preference(owner_id)
    preferences = dict(preference.preferences) if preference is not None else {}
    if ocr_provider == "llm_separate":
        return _resolve_llm_provider_from_preferences(
            preferences=preferences,
            default_llm_provider=default_llm_provider,
            provider_key="ocr_llm_provider",
            model_key="ocr_llm_model",
            base_url_key="ocr_llm_base_url",
            api_key_key="ocr_llm_api_key",
        )
    return _resolve_llm_provider_from_preferences(
        preferences=preferences,
        default_llm_provider=default_llm_provider,
    )


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
    default_llm_provider = _build_llm_provider()
    document = repository.get(document_id)
    if document is None:
        logger.error("parse task failed; document_id=%s not found", document_id)
        return {"document_id": document_id, "status": "not_found"}

    try:
        document.status = DocumentStatus.PROCESSING
        repository.save(document)

        ocr_provider = _resolve_ocr_provider_for_owner(repository, document.owner_id)
        ocr_auto_switch = _resolve_ocr_auto_switch_for_owner(repository, document.owner_id)
        metadata_llm_provider = _resolve_metadata_llm_provider_for_owner(
            repository=repository,
            owner_id=document.owner_id,
            default_llm_provider=default_llm_provider,
        )
        ocr_llm_provider = _resolve_ocr_llm_provider_for_owner(
            repository=repository,
            owner_id=document.owner_id,
            default_llm_provider=default_llm_provider,
            ocr_provider=ocr_provider,
        )
        parsed = parse_document_blob(
            document_id=document_id,
            blob_uri=blob_uri,
            ocr_provider=ocr_provider,
            llm_provider=ocr_llm_provider,
            ocr_auto_switch=ocr_auto_switch,
        )
        repository.save_parse_result(parsed)
        parse_with_llm(
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
