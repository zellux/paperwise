import json
import shutil
from typing import Any
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    ingestion_dispatcher_dependency,
    llm_provider_dependency,
    storage_dependency,
)
from paperwise.server.llm_provider import (
    resolve_http_llm_provider_from_preferences as _resolve_llm_provider_from_preferences,
)
from paperwise.server.routes.document_access import get_owned_document_or_404 as _get_owned_document_or_404
from paperwise.application.interfaces import (
    DocumentRepository,
    IngestionDispatcher,
    LLMProvider,
    StorageProvider,
)
from paperwise.application.services.documents import (
    CreateDocumentCommand,
    create_document,
    delete_document,
)
from paperwise.application.services.file_relocation import move_blob_to_processed
from paperwise.application.services.filenames import sanitize_storage_filename
from paperwise.application.services.document_listing import (
    document_sort_key as _document_sort_key,
    iter_filtered_documents as _iter_filtered_documents,
    normalized_sort_direction as _normalized_sort_direction,
    normalized_sort_field as _normalized_sort_field,
    normalized_values as _normalized_values,
)
from paperwise.application.services.history import (
    build_file_moved_history_event,
    build_metadata_history_events,
    build_processing_completed_history_event,
    build_processing_restarted_history_event,
)
from paperwise.application.services.llm_parsing import parse_with_llm
from paperwise.application.services.llm_connection_test import (
    LLMConnectionConfigError,
    LLMConnectionTestInput,
    format_llm_connection_test_error,
    run_llm_connection_test,
)
from paperwise.application.services.llm_preferences import (
    LLM_TASK_METADATA,
    LLM_TASK_OCR,
    get_normalized_llm_preferences,
)
from paperwise.application.services.parsing import parse_document_blob
from paperwise.application.services.chunk_indexing import index_document_chunks
from paperwise.application.services.storage_paths import blob_ref_to_path
from paperwise.application.services.taxonomy import (
    normalize_name as _normalize_name,
    resolve_existing_name as _resolve_existing_name,
    resolve_tags as _resolve_tags,
)
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

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


class CreateDocumentResponse(BaseModel):
    id: str
    status: str
    job_id: str | None = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    owner_id: str
    blob_uri: str
    checksum_sha256: str
    content_type: str
    size_bytes: int
    status: str
    created_at: datetime

    @classmethod
    def from_domain(cls, document: Document) -> "DocumentResponse":
        return cls.model_validate(document)


class DocumentListMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    suggested_title: str
    document_date: str | None
    correspondent: str
    document_type: str
    tags: list[str]

    @classmethod
    def from_llm_result(cls, result: LLMParseResult | None) -> "DocumentListMetadata | None":
        if result is None:
            return None
        return cls.model_validate(result)


class DocumentListItemResponse(DocumentResponse):
    llm_metadata: DocumentListMetadata | None = None

    @classmethod
    def from_domain(
        cls,
        document: Document,
        llm_result: LLMParseResult | None = None,
    ) -> "DocumentListItemResponse":
        base = DocumentResponse.from_domain(document).model_dump()
        return cls(**base, llm_metadata=DocumentListMetadata.from_llm_result(llm_result))


class ParseResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    parser: str
    status: str
    size_bytes: int
    page_count: int
    text_preview: str
    created_at: datetime

    @classmethod
    def from_domain(cls, result: ParseResult) -> "ParseResultResponse":
        return cls.model_validate(result)


class LLMParseResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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

    @classmethod
    def from_domain(cls, result: LLMParseResult) -> "LLMParseResultResponse":
        return cls.model_validate(result)


class DocumentHistoryEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    event_type: str
    actor_type: str
    actor_id: str | None
    source: str
    changes: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_domain(cls, event: DocumentHistoryEvent) -> "DocumentHistoryEventResponse":
        return cls.model_validate(event)


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
    ocr_text_preview: str | None = None
    ocr_parsed_at: datetime | None = None

    @classmethod
    def from_domain(
        cls,
        *,
        document: Document,
        llm_result: LLMParseResult | None,
        parse_result: ParseResult | None,
    ) -> "DocumentDetailResponse":
        return cls(
            document=DocumentResponse.from_domain(document),
            llm_metadata=DocumentListMetadata.from_llm_result(llm_result),
            ocr_text_preview=parse_result.text_preview if parse_result is not None else None,
            ocr_parsed_at=parse_result.created_at if parse_result is not None else None,
        )


class MetadataUpdateRequest(BaseModel):
    suggested_title: str
    document_date: str | None = None
    correspondent: str
    document_type: str
    tags: list[str]


class LLMConnectionTestRequest(BaseModel):
    task: str | None = None
    connection_name: str | None = None
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


class LLMConnectionTestResponse(BaseModel):
    ok: bool
    provider: str
    model: str
    message: str


class LocalOCRStatusResponse(BaseModel):
    available: bool
    tesseract_available: bool
    pdftoppm_available: bool
    detail: str


PENDING_STATUSES = {
    DocumentStatus.RECEIVED,
    DocumentStatus.PROCESSING,
    DocumentStatus.FAILED,
}
SUPPORTED_UPLOAD_EXTENSIONS = {
    ".doc",
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".markdown",
    ".md",
    ".pdf",
    ".png",
    ".txt",
    ".webp",
}
SUPPORTED_UPLOAD_CONTENT_TYPES = {
    "application/msword",
    "application/octet-stream",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/webp",
    "text/markdown",
    "text/plain",
}


def _normalize_content_type(value: str | None) -> str:
    return str(value or "").split(";", 1)[0].strip().lower()


def _validate_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def _is_supported_upload(*, filename: str, content_type: str | None) -> bool:
    suffix = Path(filename or "").suffix.lower()
    normalized_content_type = _normalize_content_type(content_type)
    if suffix in SUPPORTED_UPLOAD_EXTENSIONS:
        return True
    return normalized_content_type in SUPPORTED_UPLOAD_CONTENT_TYPES


def _resolve_llm_provider_for_user(
    *,
    repository: DocumentRepository,
    current_user: User,
    provider_override: LLMProvider | None,
) -> LLMProvider:
    preference = repository.get_user_preference(current_user.id)
    preferences = dict(preference.preferences) if preference is not None else {}
    return _resolve_llm_provider_from_preferences(
        preferences=preferences,
        provider_override=provider_override,
        task=LLM_TASK_METADATA,
    )


def _resolve_ocr_llm_provider_for_user(
    *,
    repository: DocumentRepository,
    current_user: User,
    provider_override: LLMProvider | None,
) -> LLMProvider:
    preference = repository.get_user_preference(current_user.id)
    preferences = dict(preference.preferences) if preference is not None else {}
    return _resolve_llm_provider_from_preferences(
        preferences=preferences,
        provider_override=provider_override,
        task=LLM_TASK_OCR,
        missing_provider_detail="Configure an OCR LLM connection in Settings before OCR parsing.",
        missing_api_key_detail="Selected OCR LLM connection requires an API key in Settings.",
        missing_base_url_detail="Custom OCR LLM connection requires a base URL in Settings.",
    )


def _resolve_ocr_provider_for_user(
    *,
    repository: DocumentRepository,
    current_user: User,
) -> str:
    preference = repository.get_user_preference(current_user.id)
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


def _resolve_ocr_auto_switch_for_user(
    *,
    repository: DocumentRepository,
    current_user: User,
) -> bool:
    preference = repository.get_user_preference(current_user.id)
    preferences = dict(preference.preferences) if preference is not None else {}
    raw = preferences.get("ocr_auto_switch", False)
    if isinstance(raw, bool):
        return raw
    normalized = str(raw).strip().lower()
    return normalized in {"true", "1", "on", "yes"}


def _resolve_file_path_from_uri(blob_uri: str) -> Path | None:
    resolved = _resolve_blob_path_from_uri(blob_uri)
    if resolved is None:
        return None
    if not resolved.exists() or not resolved.is_file():
        return None
    return resolved


def _resolve_blob_path_from_uri(blob_uri: str) -> Path | None:
    return blob_ref_to_path(blob_uri, settings.object_store_root)


def _metadata_paths_for_blob_path(blob_path: Path) -> list[Path]:
    token_prefix = blob_path.name.split("_", 1)[0].strip()
    candidates = [
        blob_path.with_name(f"{token_prefix}.metadata.json") if token_prefix else blob_path,
        blob_path.with_name(f"{blob_path.stem}.metadata.json"),
        blob_path.with_name(f"{blob_path.name}.metadata.json"),
    ]
    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique_paths.append(candidate)
    return unique_paths


def _delete_local_path_if_present(path: Path) -> None:
    if path.exists() and path.is_file():
        path.unlink()


def _cleanup_empty_storage_dirs(start: Path) -> None:
    root_dir = Path(settings.object_store_root).expanduser().resolve()
    current = start.resolve()
    while current != root_dir and root_dir in current.parents:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def _to_response(document: Document) -> DocumentResponse:
    return DocumentResponse.from_domain(document)


def _to_list_item_response(
    document: Document,
    llm_result: LLMParseResult | None,
) -> DocumentListItemResponse:
    return DocumentListItemResponse.from_domain(document, llm_result)


def _to_detail_response(
    document: Document,
    llm_result: LLMParseResult | None,
    parse_result: ParseResult | None,
) -> DocumentDetailResponse:
    return DocumentDetailResponse.from_domain(
        document=document,
        llm_result=llm_result,
        parse_result=parse_result,
    )


def _to_parse_response(result: ParseResult) -> ParseResultResponse:
    return ParseResultResponse.from_domain(result)


def _to_llm_parse_response(result: LLMParseResult) -> LLMParseResultResponse:
    return LLMParseResultResponse.from_domain(result)


def _to_history_event_response(event: DocumentHistoryEvent) -> DocumentHistoryEventResponse:
    return DocumentHistoryEventResponse.from_domain(event)


def _run_parse_document_blob_or_400(
    *,
    document_id: str,
    blob_uri: str,
    content_type: str | None,
    ocr_provider: str,
    llm_provider: LLMProvider | None,
    ocr_auto_switch: bool = False,
) -> ParseResult:
    try:
        return parse_document_blob(
            document_id=document_id,
            blob_uri=blob_uri,
            content_type=content_type,
            ocr_provider=ocr_provider,
            llm_provider=llm_provider,
            ocr_auto_switch=ocr_auto_switch,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


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
    normalized_content_type = _normalize_content_type(file.content_type) or "application/octet-stream"
    if not _is_supported_upload(filename=filename, content_type=normalized_content_type):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported upload type. Use PDF, TXT, MD, DOC, DOCX, PNG, JPG, WEBP, or GIF.",
        )
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
    storage_basename = sanitize_storage_filename(filename, reserved_prefix=f"{storage_token}_")
    storage_key = f"incoming/{date_path}/{storage_token}_{storage_basename}"
    blob_uri = storage.put(
        key=storage_key,
        data=content,
        content_type=normalized_content_type,
    )
    metadata_key = f"incoming/{date_path}/{storage_token}.metadata.json"
    metadata_payload = {
        "original_filename": filename,
        "content_type": normalized_content_type,
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
            content_type=normalized_content_type,
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
    sort_by: str | None = Query(None),
    sort_dir: str | None = Query(None),
    q: str | None = Query(None),
    tag: list[str] | None = Query(None),
    correspondent: list[str] | None = Query(None),
    document_type: list[str] | None = Query(None),
    status: list[str] | None = Query(None),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[DocumentListItemResponse]:
    normalized_tags = _normalized_values(tag)
    normalized_correspondents = _normalized_values(correspondent)
    normalized_document_types = _normalized_values(document_type)
    normalized_statuses = _normalized_values(status)
    normalized_sort_field = _normalized_sort_field(sort_by)
    normalized_sort_direction = _normalized_sort_direction(sort_dir)
    if not normalized_statuses:
        normalized_statuses = {_normalize_name(DocumentStatus.READY.value)}

    matching_documents = list(
        _iter_filtered_documents(
            repository=repository,
            current_user=current_user,
            query=q,
            normalized_tags=normalized_tags,
            normalized_correspondents=normalized_correspondents,
            normalized_document_types=normalized_document_types,
            normalized_statuses=normalized_statuses,
        )
    )
    if normalized_sort_field and normalized_sort_direction:
        matching_documents.sort(
            key=lambda item: _document_sort_key(item[0], item[1], normalized_sort_field),
            reverse=normalized_sort_direction == "desc",
        )

    results: list[DocumentListItemResponse] = []
    for document, llm_result in matching_documents[offset : offset + limit]:
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

    total = sum(
        1
        for _document, _llm_result in _iter_filtered_documents(
            repository=repository,
            current_user=current_user,
            query=q,
            normalized_tags=normalized_tags,
            normalized_correspondents=normalized_correspondents,
            normalized_document_types=normalized_document_types,
            normalized_statuses=normalized_statuses,
        )
    )
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
    provider_override: LLMProvider | None = Depends(llm_provider_dependency),
) -> LLMConnectionTestResponse:
    preference = repository.get_user_preference(current_user.id)
    base_preferences = dict(preference.preferences) if preference is not None else {}
    try:
        result = run_llm_connection_test(
            preferences=base_preferences,
            payload=LLMConnectionTestInput(
                task=payload.task,
                connection_name=payload.connection_name,
                provider=payload.provider,
                model=payload.model,
                base_url=payload.base_url,
                api_key=payload.api_key,
            ),
            provider_override=provider_override,
        )
    except LLMConnectionConfigError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM API test failed: {format_llm_connection_test_error(exc)}",
        ) from exc

    return LLMConnectionTestResponse(
        ok=True,
        provider=result.provider,
        model=result.model,
        message=f"LLM API test succeeded for {result.provider}.",
    )


@router.get("/ocr/local-status", response_model=LocalOCRStatusResponse)
def local_ocr_status_endpoint(
    current_user: User = Depends(current_user_dependency),
) -> LocalOCRStatusResponse:
    del current_user
    tesseract_available = shutil.which("tesseract") is not None
    pdftoppm_available = shutil.which("pdftoppm") is not None
    available = tesseract_available and pdftoppm_available
    if available:
        detail = "Local OCR tools are available."
    elif not tesseract_available and not pdftoppm_available:
        detail = "Local OCR unavailable: install both `tesseract` and `pdftoppm`."
    elif not tesseract_available:
        detail = "Local OCR unavailable: install `tesseract`."
    else:
        detail = "Local OCR unavailable for PDFs: install `pdftoppm`."
    return LocalOCRStatusResponse(
        available=available,
        tesseract_available=tesseract_available,
        pdftoppm_available=pdftoppm_available,
        detail=detail,
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
    parse_result = repository.get_parse_result(document_id)
    return _to_detail_response(document=document, llm_result=llm_result, parse_result=parse_result)


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


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    storage: StorageProvider = Depends(storage_dependency),
    current_user: User = Depends(current_user_dependency),
) -> None:
    document = _get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    blob_path = _resolve_blob_path_from_uri(document.blob_uri)
    metadata_paths = _metadata_paths_for_blob_path(blob_path) if blob_path is not None else []

    storage.delete(document.blob_uri)
    for metadata_path in metadata_paths:
        _delete_local_path_if_present(metadata_path)

    if blob_path is not None:
        _cleanup_empty_storage_dirs(blob_path.parent)

    delete_document(document_id=document.id, repository=repository)


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
    provider_override: LLMProvider | None = Depends(llm_provider_dependency),
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
    ocr_auto_switch = _resolve_ocr_auto_switch_for_user(
        repository=repository,
        current_user=current_user,
    )
    ocr_llm_provider: LLMProvider | None = None
    if ocr_provider == "llm":
        try:
            ocr_llm_provider = _resolve_llm_provider_for_user(
                repository=repository,
                current_user=current_user,
                provider_override=provider_override,
            )
        except HTTPException:
            ocr_llm_provider = None
    elif ocr_provider == "llm_separate":
        try:
            ocr_llm_provider = _resolve_ocr_llm_provider_for_user(
                repository=repository,
                current_user=current_user,
                provider_override=provider_override,
            )
        except HTTPException:
            ocr_llm_provider = None
    result = _run_parse_document_blob_or_400(
        document_id=document.id,
        blob_uri=document.blob_uri,
        content_type=document.content_type,
        ocr_provider=ocr_provider,
        llm_provider=ocr_llm_provider,
        ocr_auto_switch=ocr_auto_switch,
    )
    repository.save_parse_result(result)
    index_document_chunks(
        repository=repository,
        document=document,
        parse_result=result,
    )
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
    provider_override: LLMProvider | None = Depends(llm_provider_dependency),
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
        provider_override=provider_override,
    )
    ocr_provider = _resolve_ocr_provider_for_user(
        repository=repository,
        current_user=current_user,
    )
    ocr_auto_switch = _resolve_ocr_auto_switch_for_user(
        repository=repository,
        current_user=current_user,
    )
    ocr_llm_provider: LLMProvider | None = None
    if ocr_provider == "llm":
        ocr_llm_provider = llm_provider
    elif ocr_provider == "llm_separate":
        try:
            ocr_llm_provider = _resolve_ocr_llm_provider_for_user(
                repository=repository,
                current_user=current_user,
                provider_override=provider_override,
            )
        except HTTPException:
            ocr_llm_provider = None
    try:
        parse_result = repository.get_parse_result(document_id)
        if parse_result is None:
            _set_document_status(
                document=document,
                repository=repository,
                status_value=DocumentStatus.PROCESSING,
            )
            parse_result = _run_parse_document_blob_or_400(
                document_id=document.id,
                blob_uri=document.blob_uri,
                content_type=document.content_type,
                ocr_provider=ocr_provider,
                llm_provider=ocr_llm_provider,
                ocr_auto_switch=ocr_auto_switch,
            )
            repository.save_parse_result(parse_result)
            index_document_chunks(
                repository=repository,
                document=document,
                parse_result=parse_result,
            )
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
                parse_result=parse_result,
                llm_result=result,
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
    return [
        TagStatResponse(tag=tag, document_count=count)
        for tag, count in repository.list_owner_tag_stats(current_user.id)
    ]


@router.get("/metadata/document-type-stats", response_model=list[DocumentTypeStatResponse])
def get_document_type_stats_endpoint(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[DocumentTypeStatResponse]:
    return [
        DocumentTypeStatResponse(document_type=document_type, document_count=count)
        for document_type, count in repository.list_owner_document_type_stats(current_user.id)
    ]
