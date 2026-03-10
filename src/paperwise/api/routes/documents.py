import json
import re
from typing import Any
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from paperwise.api.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    ingestion_dispatcher_dependency,
    llm_provider_dependency,
    storage_dependency,
)
from paperwise.application.interfaces import (
    DocumentRepository,
    IngestionDispatcher,
    LLMProvider,
    StorageProvider,
)
from paperwise.application.services.documents import CreateDocumentCommand, create_document, get_document
from paperwise.application.services.file_relocation import move_blob_to_processed
from paperwise.application.services.history import (
    build_file_moved_history_event,
    build_metadata_history_events,
    build_processing_completed_history_event,
    build_processing_restarted_history_event,
)
from paperwise.application.services.llm_parsing import parse_with_llm
from paperwise.application.services.parsing import parse_document_blob
from paperwise.application.services.storage_paths import blob_ref_to_path
from paperwise.domain.models import (
    Document,
    DocumentHistoryEvent,
    DocumentStatus,
    HistoryActorType,
    LLMParseResult,
    ParseResult,
    User,
)
from paperwise.infrastructure.config import get_settings
from paperwise.infrastructure.llm.anthropic_llm_provider import AnthropicLLMProvider
from paperwise.infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from paperwise.infrastructure.llm.openai_llm_provider import OpenAILLMProvider
from paperwise.infrastructure.llm.simple_llm_provider import SimpleLLMProvider
from paperwise.infrastructure.llm.missing_openai_provider import MissingOpenAIProvider

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


class CreateDocumentResponse(BaseModel):
    id: str
    status: str
    job_id: str | None = None


class DocumentResponse(BaseModel):
    id: str
    filename: str
    owner_id: str
    blob_uri: str
    checksum_sha256: str
    content_type: str
    size_bytes: int
    status: str
    created_at: datetime


class DocumentListMetadata(BaseModel):
    suggested_title: str
    document_date: str | None
    correspondent: str
    document_type: str
    tags: list[str]


class DocumentListItemResponse(DocumentResponse):
    llm_metadata: DocumentListMetadata | None = None


class ParseResultResponse(BaseModel):
    document_id: str
    parser: str
    status: str
    size_bytes: int
    page_count: int
    text_preview: str
    created_at: datetime


class LLMParseResultResponse(BaseModel):
    document_id: str
    suggested_title: str
    document_date: str | None
    correspondent: str
    document_type: str
    tags: list[str]
    created_correspondent: bool
    created_document_type: bool
    created_tags: list[str]
    created_at: datetime


class DocumentHistoryEventResponse(BaseModel):
    id: str
    document_id: str
    event_type: str
    actor_type: str
    actor_id: str | None
    source: str
    changes: dict[str, Any]
    created_at: datetime


class TaxonomyResponse(BaseModel):
    correspondents: list[str]
    document_types: list[str]
    tags: list[str]


class TagStatResponse(BaseModel):
    tag: str
    document_count: int


class DocumentTypeStatResponse(BaseModel):
    document_type: str
    document_count: int


class RestartPendingResponse(BaseModel):
    restarted_count: int
    skipped_ready_count: int


class CountResponse(BaseModel):
    total: int


class DocumentDetailResponse(BaseModel):
    document: DocumentResponse
    llm_metadata: DocumentListMetadata | None = None


class MetadataUpdateRequest(BaseModel):
    suggested_title: str
    document_date: str | None = None
    correspondent: str
    document_type: str
    tags: list[str]


class LLMConnectionTestRequest(BaseModel):
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


class LLMConnectionTestResponse(BaseModel):
    ok: bool
    provider: str
    model: str
    message: str


PENDING_STATUSES = {
    DocumentStatus.RECEIVED,
    DocumentStatus.PROCESSING,
}


def _normalize_name(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return " ".join(cleaned.split())


def _to_title_case(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return cleaned

    def looks_like_acronym_token(token: str) -> bool:
        letters = "".join(ch for ch in token if ch.isalpha())
        if not letters or not letters.isalpha():
            return False
        if len(letters) < 2 or len(letters) > 6:
            return False
        vowels = sum(ch in "aeiou" for ch in letters.lower())
        return vowels == 0

    words: list[str] = []
    for word in cleaned.split(" "):
        letters = "".join(ch for ch in word if ch.isalpha())
        if len(letters) >= 2 and letters.isupper():
            words.append(word)
            continue
        if looks_like_acronym_token(word):
            words.append(word.upper())
            continue
        if word.islower():
            words.append(word[:1].upper() + word[1:] if word else word)
            continue
        words.append(word)
    return " ".join(words)


def _resolve_existing_name(candidate: str, existing: list[str], fallback: str) -> tuple[str, bool]:
    normalized_candidate = _normalize_name(candidate)
    if not normalized_candidate:
        return fallback, False
    for name in existing:
        if _normalize_name(name) == normalized_candidate:
            return name, False
    return _to_title_case(candidate), True


def _validate_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def _resolve_tags(candidate_tags: list[str], existing_tags: list[str]) -> tuple[list[str], list[str]]:
    existing_by_norm = {_normalize_name(tag): _to_title_case(tag) for tag in existing_tags}
    resolved: list[str] = []
    created: list[str] = []
    seen: set[str] = set()
    for tag in candidate_tags:
        normalized = _normalize_name(tag)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        if normalized in existing_by_norm:
            resolved.append(existing_by_norm[normalized])
            continue
        created_tag = _to_title_case(tag)
        resolved.append(created_tag)
        created.append(created_tag)
    return resolved, created


def _normalized_values(values: list[str] | None) -> set[str]:
    normalized: set[str] = set()
    for value in values or []:
        for part in value.split(","):
            item = _normalize_name(part)
            if item:
                normalized.add(item)
    return normalized


def _matches_text_query(
    *,
    query: str | None,
    document: Document,
    llm_result: LLMParseResult | None,
) -> bool:
    normalized_query = " ".join(str(query or "").strip().casefold().split())
    if not normalized_query:
        return True

    candidates = [document.filename]
    if llm_result is not None:
        candidates.extend(
            [
                llm_result.suggested_title,
                llm_result.correspondent,
                llm_result.document_type,
                llm_result.document_date or "",
                " ".join(llm_result.tags),
            ]
        )

    haystack = " ".join(" ".join(str(value).split()) for value in candidates).casefold()
    return normalized_query in haystack


def _matches_document_filters(
    *,
    document: Document,
    llm_result: LLMParseResult | None,
    normalized_tags: set[str],
    normalized_correspondents: set[str],
    normalized_document_types: set[str],
    normalized_statuses: set[str],
    query: str | None,
) -> bool:
    if normalized_statuses and _normalize_name(document.status.value) not in normalized_statuses:
        return False
    if normalized_tags:
        if llm_result is None or not normalized_tags.intersection({_normalize_name(item) for item in llm_result.tags}):
            return False
    if normalized_correspondents:
        if llm_result is None or _normalize_name(llm_result.correspondent) not in normalized_correspondents:
            return False
    if normalized_document_types:
        if llm_result is None or _normalize_name(llm_result.document_type) not in normalized_document_types:
            return False
    if not _matches_text_query(query=query, document=document, llm_result=llm_result):
        return False
    return True


def _sanitize_filename(value: str) -> str:
    cleaned = Path(value).name.strip()
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    if not cleaned:
        return "uploaded-document.bin"
    return cleaned


def _resolve_llm_provider_for_user(
    *,
    repository: DocumentRepository,
    current_user: User,
    default_llm_provider: LLMProvider,
) -> LLMProvider:
    preference = repository.get_user_preference(current_user.id)
    preferences = dict(preference.preferences) if preference is not None else {}
    return _resolve_llm_provider_from_preferences(
        preferences=preferences,
        default_llm_provider=default_llm_provider,
    )


def _resolve_llm_provider_from_preferences(
    *,
    preferences: dict[str, Any],
    default_llm_provider: LLMProvider,
) -> LLMProvider:
    provider_name = str(preferences.get("llm_provider", "")).strip().lower()

    # Preserve testability when a fake provider is injected via dependency override.
    if not isinstance(
        default_llm_provider,
        (MissingOpenAIProvider, OpenAILLMProvider, AnthropicLLMProvider, GeminiLLMProvider, SimpleLLMProvider),
    ):
        return default_llm_provider

    if not provider_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configure an LLM provider in Settings before running LLM parse.",
        )

    configured_key = str(preferences.get("llm_api_key", "")).strip()
    if not configured_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected LLM provider requires your API key in Settings.",
        )

    if provider_name == "openai":
        configured_key = str(preferences.get("llm_api_key", "")).strip()
        api_key = configured_key
        model = str(preferences.get("llm_model", "")).strip() or settings.openai_model
        base_url = str(preferences.get("llm_base_url", "")).strip() or settings.openai_base_url
        return OpenAILLMProvider(
            api_key=api_key,
            model=model,
            base_url=base_url,
        )
    if provider_name == "claude":
        model = str(preferences.get("llm_model", "")).strip() or "claude-3-5-sonnet-latest"
        base_url = str(preferences.get("llm_base_url", "")).strip() or "https://api.anthropic.com"
        return AnthropicLLMProvider(
            api_key=configured_key,
            model=model,
            base_url=base_url,
        )
    if provider_name == "gemini":
        model = str(preferences.get("llm_model", "")).strip() or "gemini-2.0-flash"
        base_url = str(preferences.get("llm_base_url", "")).strip() or "https://generativelanguage.googleapis.com/v1beta"
        return GeminiLLMProvider(
            api_key=configured_key,
            model=model,
            base_url=base_url,
        )
    if provider_name == "custom":
        base_url = str(preferences.get("llm_base_url", "")).strip()
        if not base_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom LLM provider requires a base URL in Settings.",
            )
        model = str(preferences.get("llm_model", "")).strip() or settings.openai_model
        return OpenAILLMProvider(
            api_key=configured_key,
            model=model,
            base_url=base_url,
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported LLM provider: {provider_name}",
    )


def _merge_llm_preferences(
    preferences: dict[str, Any],
    payload: LLMConnectionTestRequest,
) -> dict[str, Any]:
    merged = dict(preferences)
    if payload.provider is not None:
        merged["llm_provider"] = payload.provider
    if payload.model is not None:
        merged["llm_model"] = payload.model
    if payload.base_url is not None:
        merged["llm_base_url"] = payload.base_url
    if payload.api_key is not None:
        merged["llm_api_key"] = payload.api_key
    return merged


def _resolve_ocr_provider_for_user(
    *,
    repository: DocumentRepository,
    current_user: User,
) -> str:
    preference = repository.get_user_preference(current_user.id)
    preferences = dict(preference.preferences) if preference is not None else {}
    provider_name = str(preferences.get("ocr_provider", "llm")).strip().lower()
    if provider_name in {"tesseract", "llm"}:
        return provider_name
    return "llm"


def _resolve_file_path_from_uri(blob_uri: str) -> Path | None:
    resolved = blob_ref_to_path(blob_uri, settings.object_store_root)
    if resolved is None:
        return None
    if not resolved.exists() or not resolved.is_file():
        return None
    return resolved


def _to_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        owner_id=document.owner_id,
        blob_uri=document.blob_uri,
        checksum_sha256=document.checksum_sha256,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        status=document.status.value,
        created_at=document.created_at,
    )


def _to_list_item_response(
    document: Document,
    llm_result: LLMParseResult | None,
) -> DocumentListItemResponse:
    metadata = None
    if llm_result is not None:
        metadata = DocumentListMetadata(
            suggested_title=llm_result.suggested_title,
            document_date=llm_result.document_date,
            correspondent=llm_result.correspondent,
            document_type=llm_result.document_type,
            tags=llm_result.tags,
        )
    return DocumentListItemResponse(
        id=document.id,
        filename=document.filename,
        owner_id=document.owner_id,
        blob_uri=document.blob_uri,
        checksum_sha256=document.checksum_sha256,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        status=document.status.value,
        created_at=document.created_at,
        llm_metadata=metadata,
    )


def _to_detail_response(
    document: Document,
    llm_result: LLMParseResult | None,
) -> DocumentDetailResponse:
    return DocumentDetailResponse(
        document=_to_response(document),
        llm_metadata=(
            DocumentListMetadata(
                suggested_title=llm_result.suggested_title,
                document_date=llm_result.document_date,
                correspondent=llm_result.correspondent,
                document_type=llm_result.document_type,
                tags=llm_result.tags,
            )
            if llm_result is not None
            else None
        ),
    )


def _to_parse_response(result: ParseResult) -> ParseResultResponse:
    return ParseResultResponse(
        document_id=result.document_id,
        parser=result.parser,
        status=result.status,
        size_bytes=result.size_bytes,
        page_count=result.page_count,
        text_preview=result.text_preview,
        created_at=result.created_at,
    )


def _to_llm_parse_response(result: LLMParseResult) -> LLMParseResultResponse:
    return LLMParseResultResponse(
        document_id=result.document_id,
        suggested_title=result.suggested_title,
        document_date=result.document_date,
        correspondent=result.correspondent,
        document_type=result.document_type,
        tags=result.tags,
        created_correspondent=result.created_correspondent,
        created_document_type=result.created_document_type,
        created_tags=result.created_tags,
        created_at=result.created_at,
    )


def _to_history_event_response(event: DocumentHistoryEvent) -> DocumentHistoryEventResponse:
    return DocumentHistoryEventResponse(
        id=event.id,
        document_id=event.document_id,
        event_type=event.event_type.value,
        actor_type=event.actor_type.value,
        actor_id=event.actor_id,
        source=event.source,
        changes=event.changes,
        created_at=event.created_at,
    )


def _set_document_status(
    *,
    document: Document,
    repository: DocumentRepository,
    status_value: DocumentStatus,
) -> Document:
    if document.status == status_value:
        return document
    document.status = status_value
    repository.save(document)
    return document


def _get_owned_document_or_404(
    *,
    document_id: str,
    repository: DocumentRepository,
    current_user: User,
) -> Document:
    document = get_document(document_id=document_id, repository=repository)
    if document is None or document.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateDocumentResponse,
)
def create_document_endpoint(
    owner_id: str = Form(""),
    file: UploadFile = File(...),
    repository: DocumentRepository = Depends(document_repository_dependency),
    dispatcher: IngestionDispatcher = Depends(ingestion_dispatcher_dependency),
    storage: StorageProvider = Depends(storage_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CreateDocumentResponse:
    del owner_id
    filename = file.filename or "uploaded-document"
    content = file.file.read()
    checksum = sha256(content).hexdigest()
    existing = repository.get_by_owner_checksum(current_user.id, checksum)
    if existing is not None:
        return CreateDocumentResponse(
            id=existing.id,
            status=existing.status.value,
            job_id=None,
        )
    now = datetime.now(UTC)
    date_path = now.strftime("%Y/%m/%d")
    storage_token = str(uuid4())
    storage_key = f"incoming/{date_path}/{storage_token}_{_sanitize_filename(filename)}"
    blob_uri = storage.put(
        key=storage_key,
        data=content,
        content_type=file.content_type or "application/octet-stream",
    )
    metadata_key = f"incoming/{date_path}/{storage_token}.metadata.json"
    metadata_payload = {
        "original_filename": filename,
        "content_type": file.content_type or "application/octet-stream",
        "checksum_sha256": checksum,
        "size_bytes": len(content),
        "stored_key": storage_key,
        "stored_at": now.isoformat(),
    }
    storage.put(
        key=metadata_key,
        data=json.dumps(metadata_payload, ensure_ascii=True, indent=2).encode("utf-8"),
        content_type="application/json",
    )

    document, job_id = create_document(
        CreateDocumentCommand(
            filename=filename,
            owner_id=current_user.id,
            blob_uri=blob_uri,
            checksum_sha256=checksum,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=len(content),
        ),
        repository=repository,
        dispatcher=dispatcher,
    )
    return CreateDocumentResponse(
        id=document.id,
        status=document.status.value,
        job_id=job_id,
    )


@router.get("", response_model=list[DocumentListItemResponse])
def list_documents_endpoint(
    limit: int = 100,
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
    tag: list[str] | None = Query(None),
    correspondent: list[str] | None = Query(None),
    document_type: list[str] | None = Query(None),
    status: list[str] | None = Query(None),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[DocumentListItemResponse]:
    documents = repository.list_documents(limit=limit, offset=offset)
    normalized_tags = _normalized_values(tag)
    normalized_correspondents = _normalized_values(correspondent)
    normalized_document_types = _normalized_values(document_type)
    normalized_statuses = _normalized_values(status)
    if not normalized_statuses:
        normalized_statuses = {_normalize_name(DocumentStatus.READY.value)}

    results: list[DocumentListItemResponse] = []
    for document in documents:
        if document.owner_id != current_user.id:
            continue
        llm_result = repository.get_llm_parse_result(document.id)
        if not _matches_document_filters(
            document=document,
            llm_result=llm_result,
            normalized_tags=normalized_tags,
            normalized_correspondents=normalized_correspondents,
            normalized_document_types=normalized_document_types,
            normalized_statuses=normalized_statuses,
            query=q,
        ):
            continue
        results.append(
            _to_list_item_response(
                document=document,
                llm_result=llm_result,
            )
        )
    return results


@router.get("/count", response_model=CountResponse)
def count_documents_endpoint(
    q: str | None = Query(None),
    tag: list[str] | None = Query(None),
    correspondent: list[str] | None = Query(None),
    document_type: list[str] | None = Query(None),
    status: list[str] | None = Query(None),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CountResponse:
    normalized_tags = _normalized_values(tag)
    normalized_correspondents = _normalized_values(correspondent)
    normalized_document_types = _normalized_values(document_type)
    normalized_statuses = _normalized_values(status)
    if not normalized_statuses:
        normalized_statuses = {_normalize_name(DocumentStatus.READY.value)}

    total = 0
    batch_size = 1000
    offset = 0
    while True:
        documents = repository.list_documents(limit=batch_size, offset=offset)
        if not documents:
            break
        for document in documents:
            if document.owner_id != current_user.id:
                continue
            llm_result = repository.get_llm_parse_result(document.id)
            if not _matches_document_filters(
                document=document,
                llm_result=llm_result,
                normalized_tags=normalized_tags,
                normalized_correspondents=normalized_correspondents,
                normalized_document_types=normalized_document_types,
                normalized_statuses=normalized_statuses,
                query=q,
            ):
                continue
            total += 1
        if len(documents) < batch_size:
            break
        offset += batch_size
    return CountResponse(total=total)


@router.get("/pending", response_model=list[DocumentListItemResponse])
def list_pending_documents_endpoint(
    limit: int = 100,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[DocumentListItemResponse]:
    documents = repository.list_documents(limit=limit)
    pending_docs = [
        document
        for document in documents
        if document.status in PENDING_STATUSES and document.owner_id == current_user.id
    ]
    return [
        _to_list_item_response(
            document=document,
            llm_result=repository.get_llm_parse_result(document.id),
        )
        for document in pending_docs
    ]


@router.post("/pending/restart", response_model=RestartPendingResponse)
def restart_pending_documents_endpoint(
    limit: int = 100,
    repository: DocumentRepository = Depends(document_repository_dependency),
    dispatcher: IngestionDispatcher = Depends(ingestion_dispatcher_dependency),
    current_user: User = Depends(current_user_dependency),
) -> RestartPendingResponse:
    documents = repository.list_documents(limit=limit)
    restarted_count = 0
    skipped_ready_count = 0
    history_events: list[DocumentHistoryEvent] = []

    for document in documents:
        if document.owner_id != current_user.id:
            continue
        if document.status == DocumentStatus.READY:
            skipped_ready_count += 1
            continue
        previous_status = document.status.value
        _set_document_status(
            document=document,
            repository=repository,
            status_value=DocumentStatus.PROCESSING,
        )
        dispatcher.enqueue(
            document_id=document.id,
            blob_uri=document.blob_uri,
            filename=document.filename,
            content_type=document.content_type,
        )
        history_events.append(
            build_processing_restarted_history_event(
                document_id=document.id,
                actor_type=HistoryActorType.USER,
                actor_id=current_user.id,
                source="api.pending_restart",
                previous_status=previous_status,
                current_status=document.status.value,
            )
        )
        restarted_count += 1

    repository.append_history_events(history_events)
    return RestartPendingResponse(
        restarted_count=restarted_count,
        skipped_ready_count=skipped_ready_count,
    )


@router.post("/llm/test", response_model=LLMConnectionTestResponse)
def test_llm_connection_endpoint(
    payload: LLMConnectionTestRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
    default_llm_provider: LLMProvider = Depends(llm_provider_dependency),
) -> LLMConnectionTestResponse:
    preference = repository.get_user_preference(current_user.id)
    base_preferences = dict(preference.preferences) if preference is not None else {}
    merged_preferences = _merge_llm_preferences(base_preferences, payload)
    llm_provider = _resolve_llm_provider_from_preferences(
        preferences=merged_preferences,
        default_llm_provider=default_llm_provider,
    )
    provider_name = str(merged_preferences.get("llm_provider", "")).strip().lower() or "custom"
    model_name = str(merged_preferences.get("llm_model", "")).strip() or "default"
    try:
        llm_provider.suggest_metadata(
            filename="connection-test.txt",
            text_preview="Connection test sample.",
            current_correspondent=None,
            current_document_type=None,
            existing_correspondents=[],
            existing_document_types=[],
            existing_tags=["Test"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM API test failed: {exc}",
        ) from exc

    return LLMConnectionTestResponse(
        ok=True,
        provider=provider_name,
        model=model_name,
        message=f"LLM API test succeeded for {provider_name}.",
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> DocumentResponse:
    document = _get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    return _to_response(document)


@router.get("/{document_id}/detail", response_model=DocumentDetailResponse)
def get_document_detail_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> DocumentDetailResponse:
    document = _get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    llm_result = repository.get_llm_parse_result(document_id)
    return _to_detail_response(document=document, llm_result=llm_result)


@router.get("/{document_id}/file")
def get_document_file_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> FileResponse:
    document = _get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    file_path = _resolve_file_path_from_uri(document.blob_uri)
    if file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found",
        )
    return FileResponse(
        path=file_path,
        media_type=document.content_type or "application/octet-stream",
        filename=document.filename,
        content_disposition_type="inline",
    )


@router.post("/{document_id}/reprocess", response_model=CreateDocumentResponse)
def reprocess_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    dispatcher: IngestionDispatcher = Depends(ingestion_dispatcher_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CreateDocumentResponse:
    document = _get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )

    previous_status = document.status.value
    _set_document_status(
        document=document,
        repository=repository,
        status_value=DocumentStatus.PROCESSING,
    )
    job_id = dispatcher.enqueue(
        document_id=document.id,
        blob_uri=document.blob_uri,
        filename=document.filename,
        content_type=document.content_type,
    )
    repository.append_history_events(
        [
            build_processing_restarted_history_event(
                document_id=document.id,
                actor_type=HistoryActorType.USER,
                actor_id=current_user.id,
                source="api.reprocess",
                previous_status=previous_status,
                current_status=document.status.value,
            )
        ]
    )
    return CreateDocumentResponse(
        id=document.id,
        status=document.status.value,
        job_id=job_id,
    )


@router.post("/{document_id}/parse", response_model=ParseResultResponse)
def parse_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> ParseResultResponse:
    document = _get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    _set_document_status(
        document=document,
        repository=repository,
        status_value=DocumentStatus.PROCESSING,
    )
    ocr_provider = _resolve_ocr_provider_for_user(
        repository=repository,
        current_user=current_user,
    )
    try:
        result = parse_document_blob(
            document_id=document.id,
            blob_uri=document.blob_uri,
            ocr_provider=ocr_provider,
        )
        repository.save_parse_result(result)
    except Exception:
        raise
    return _to_parse_response(result)


@router.get("/{document_id}/parse", response_model=ParseResultResponse)
def get_parse_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> ParseResultResponse:
    _get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    result = repository.get_parse_result(document_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parse result not found",
        )
    return _to_parse_response(result)


@router.post("/{document_id}/llm-parse", response_model=LLMParseResultResponse)
def llm_parse_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    default_llm_provider: LLMProvider = Depends(llm_provider_dependency),
    current_user: User = Depends(current_user_dependency),
) -> LLMParseResultResponse:
    document = _get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    llm_provider = _resolve_llm_provider_for_user(
        repository=repository,
        current_user=current_user,
        default_llm_provider=default_llm_provider,
    )
    ocr_provider = _resolve_ocr_provider_for_user(
        repository=repository,
        current_user=current_user,
    )
    try:
        parse_result = repository.get_parse_result(document_id)
        if parse_result is None:
            _set_document_status(
                document=document,
                repository=repository,
                status_value=DocumentStatus.PROCESSING,
            )
            parse_result = parse_document_blob(
                document_id=document.id,
                blob_uri=document.blob_uri,
                ocr_provider=ocr_provider,
            )
            repository.save_parse_result(parse_result)
        else:
            _set_document_status(
                document=document,
                repository=repository,
                status_value=DocumentStatus.PROCESSING,
            )
        result = parse_with_llm(
            document=document,
            parse_result=parse_result,
            repository=repository,
            llm_provider=llm_provider,
            actor_type=HistoryActorType.USER,
            actor_id=current_user.id,
            history_source="api.llm_parse",
        )
    except Exception:
        raise

    _set_document_status(
        document=document,
        repository=repository,
        status_value=DocumentStatus.READY,
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
    repository.save(document)
    repository.append_history_events(
        [
            build_processing_completed_history_event(
                document_id=document.id,
                actor_type=HistoryActorType.USER,
                actor_id=current_user.id,
                source="api.llm_parse",
                previous_status=DocumentStatus.PROCESSING.value,
                current_status=document.status.value,
            )
        ]
    )
    file_move_event = build_file_moved_history_event(
        document_id=document.id,
        actor_type=HistoryActorType.USER,
        actor_id=current_user.id,
        source="api.llm_parse",
        from_blob_uri=previous_blob_uri,
        to_blob_uri=document.blob_uri,
    )
    if file_move_event is not None:
        repository.append_history_events([file_move_event])
    return _to_llm_parse_response(result)


@router.get("/{document_id}/llm-parse", response_model=LLMParseResultResponse)
def get_llm_parse_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> LLMParseResultResponse:
    _get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    result = repository.get_llm_parse_result(document_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM parse result not found",
        )
    return _to_llm_parse_response(result)


@router.patch("/{document_id}/metadata", response_model=LLMParseResultResponse)
def update_document_metadata_endpoint(
    document_id: str,
    payload: MetadataUpdateRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> LLMParseResultResponse:
    document = _get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )

    correspondents = repository.list_correspondents()
    document_types = repository.list_document_types()
    existing_tags = repository.list_tags()

    correspondent, created_correspondent = _resolve_existing_name(
        payload.correspondent,
        correspondents,
        fallback="Unknown Sender",
    )
    document_type, created_document_type = _resolve_existing_name(
        payload.document_type,
        document_types,
        fallback="General Document",
    )
    tags, created_tags = _resolve_tags(payload.tags, existing_tags)

    if created_correspondent:
        repository.add_correspondent(correspondent)
    if created_document_type:
        repository.add_document_type(document_type)
    if created_tags:
        repository.add_tags(created_tags)

    previous = repository.get_llm_parse_result(document_id)
    result = LLMParseResult(
        document_id=document_id,
        suggested_title=payload.suggested_title.strip() or document.filename,
        document_date=_validate_date(payload.document_date),
        correspondent=correspondent,
        document_type=document_type,
        tags=tags,
        created_correspondent=created_correspondent,
        created_document_type=created_document_type,
        created_tags=created_tags,
        created_at=datetime.now(UTC),
    )
    repository.save_llm_parse_result(result)
    repository.append_history_events(
        build_metadata_history_events(
            previous=previous,
            current=result,
            actor_type=HistoryActorType.USER,
            actor_id=current_user.id,
            source="api.patch_metadata",
        )
    )
    _set_document_status(
        document=document,
        repository=repository,
        status_value=DocumentStatus.READY,
    )
    return _to_llm_parse_response(result)


@router.get("/{document_id}/history", response_model=list[DocumentHistoryEventResponse])
def list_document_history_endpoint(
    document_id: str,
    limit: int = Query(100, ge=1, le=500),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[DocumentHistoryEventResponse]:
    _get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    return [
        _to_history_event_response(event)
        for event in repository.list_history(document_id=document_id, limit=limit)
    ]


@router.get("/metadata/taxonomy", response_model=TaxonomyResponse)
def get_taxonomy_endpoint(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> TaxonomyResponse:
    del current_user
    return TaxonomyResponse(
        correspondents=repository.list_correspondents(),
        document_types=repository.list_document_types(),
        tags=repository.list_tags(),
    )


@router.get("/metadata/tag-stats", response_model=list[TagStatResponse])
def get_tag_stats_endpoint(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[TagStatResponse]:
    counts: dict[str, int] = {}
    display_name_by_key: dict[str, str] = {}
    documents = repository.list_documents(limit=10_000)
    for document in documents:
        if document.owner_id != current_user.id:
            continue
        llm_result = repository.get_llm_parse_result(document.id)
        if llm_result is None:
            continue
        seen_tags: set[str] = set()
        for tag in llm_result.tags:
            cleaned = str(tag).strip()
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen_tags:
                continue
            seen_tags.add(key)
            if key not in display_name_by_key:
                display_name_by_key[key] = _to_title_case(cleaned)
            counts[key] = counts.get(key, 0) + 1
    return [
        TagStatResponse(tag=display_name_by_key[key], document_count=count)
        for key, count in sorted(
            counts.items(),
            key=lambda item: (-item[1], display_name_by_key[item[0]].casefold()),
        )
    ]


@router.get("/metadata/document-type-stats", response_model=list[DocumentTypeStatResponse])
def get_document_type_stats_endpoint(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[DocumentTypeStatResponse]:
    counts: dict[str, int] = {}
    display_name_by_key: dict[str, str] = {}
    documents = repository.list_documents(limit=10_000)
    for document in documents:
        if document.owner_id != current_user.id:
            continue
        llm_result = repository.get_llm_parse_result(document.id)
        if llm_result is None:
            continue
        cleaned = str(llm_result.document_type).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key not in display_name_by_key:
            display_name_by_key[key] = _to_title_case(cleaned)
        counts[key] = counts.get(key, 0) + 1
    return [
        DocumentTypeStatResponse(document_type=display_name_by_key[key], document_count=count)
        for key, count in sorted(
            counts.items(),
            key=lambda item: (-item[1], display_name_by_key[item[0]].casefold()),
        )
    ]
