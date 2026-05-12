import json
import shutil
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    ingestion_dispatcher_dependency,
    llm_provider_dependency,
    settings_dependency,
    storage_dependency,
)
from paperwise.server.http_llm_provider import (
    resolve_http_metadata_llm_provider_for_user,
    resolve_http_ocr_llm_provider_for_user,
)
from paperwise.server.document_access import get_owned_document_or_404
from paperwise.server.schemas.documents import (
    CountResponse,
    CreateDocumentResponse,
    DocumentDetailResponse,
    DocumentHistoryEventResponse,
    DocumentListItemResponse,
    DocumentResponse,
    DocumentStarredRequest,
    DocumentTypeStatResponse,
    LLMConnectionTestResponse,
    LLMParseResultResponse,
    LocalOCRStatusResponse,
    ParseResultResponse,
    RestartPendingResponse,
    TagStatResponse,
    TaxonomyResponse,
    LLMConnectionTestRequest,
    MetadataUpdateRequest,
)
from paperwise.server.presenters.documents import (
    present_document,
    present_document_detail,
    present_document_history_event,
    present_document_list_item,
    present_llm_parse_result,
    present_parse_result,
)
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
from paperwise.application.services.document_file_cleanup import (
    cleanup_empty_storage_dirs,
    delete_local_path_if_present,
    metadata_paths_for_blob_path,
    resolve_blob_path_from_uri,
    resolve_file_path_from_uri,
)
from paperwise.application.services.filenames import sanitize_storage_filename
from paperwise.application.services.document_listing import count_filtered_documents, list_filtered_documents
from paperwise.application.services.history import (
    build_processing_restarted_history_event,
)
from paperwise.application.services.document_pipeline import process_document
from paperwise.application.services.llm_connection_test import (
    LLMConnectionConfigError,
    LLMConnectionTestInput,
    format_llm_connection_test_error,
    run_llm_connection_test,
)
from paperwise.application.services.metadata_updates import update_document_metadata
from paperwise.application.services.ocr_preferences import (
    resolve_owner_ocr_auto_switch,
    resolve_owner_ocr_provider,
)
from paperwise.application.services.parsing import parse_document_blob
from paperwise.application.services.pending_documents import (
    list_pending_documents,
    restart_pending_documents,
)
from paperwise.application.services.chunk_indexing import index_document_chunks
from paperwise.application.services.upload_validation import (
    is_supported_upload,
    normalize_content_type,
)
from paperwise.application.services.user_preferences import load_user_preferences
from paperwise.domain.models import (
    Document,
    DocumentStatus,
    HistoryActorType,
    ParseResult,
    User,
)
from paperwise.infrastructure.config import Settings

router = APIRouter(prefix="/documents", tags=["documents"])


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
    normalized_content_type = normalize_content_type(file.content_type) or "application/octet-stream"
    if not is_supported_upload(filename=filename, content_type=normalized_content_type):
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
    starred: bool = Query(False),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[DocumentListItemResponse]:
    listing = list_filtered_documents(
        repository=repository,
        current_user=current_user,
        query=q,
        tag=tag,
        correspondent=correspondent,
        document_type=document_type,
        status=status,
        starred=starred,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )
    return [
        present_document_list_item(document=document, llm_result=llm_result)
        for document, llm_result in listing.rows
    ]


@router.get("/count", response_model=CountResponse)
def count_documents_endpoint(
    q: str | None = Query(None),
    tag: list[str] | None = Query(None),
    correspondent: list[str] | None = Query(None),
    document_type: list[str] | None = Query(None),
    status: list[str] | None = Query(None),
    starred: bool = Query(False),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CountResponse:
    return CountResponse(
        total=count_filtered_documents(
            repository=repository,
            current_user=current_user,
            query=q,
            tag=tag,
            correspondent=correspondent,
            document_type=document_type,
            status=status,
            starred=starred,
        )
    )


@router.get("/pending", response_model=list[DocumentListItemResponse])
def list_pending_documents_endpoint(
    limit: int = 100,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[DocumentListItemResponse]:
    return [
        present_document_list_item(
            document=document,
            llm_result=llm_result,
        )
        for document, llm_result in list_pending_documents(
            repository=repository,
            owner_id=current_user.id,
            limit=limit,
        )
    ]


@router.post("/pending/restart", response_model=RestartPendingResponse)
def restart_pending_documents_endpoint(
    limit: int = 100,
    repository: DocumentRepository = Depends(document_repository_dependency),
    dispatcher: IngestionDispatcher = Depends(ingestion_dispatcher_dependency),
    current_user: User = Depends(current_user_dependency),
) -> RestartPendingResponse:
    result = restart_pending_documents(
        repository=repository,
        dispatcher=dispatcher,
        owner_id=current_user.id,
        actor_id=current_user.id,
        limit=limit,
    )
    return RestartPendingResponse(
        restarted_count=result.restarted_count,
        skipped_ready_count=result.skipped_ready_count,
    )


@router.post("/llm/test", response_model=LLMConnectionTestResponse)
def test_llm_connection_endpoint(
    payload: LLMConnectionTestRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
    provider_override: LLMProvider | None = Depends(llm_provider_dependency),
) -> LLMConnectionTestResponse:
    try:
        result = run_llm_connection_test(
            preferences=load_user_preferences(repository=repository, user_id=current_user.id),
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
    document = get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    return present_document(document)


@router.get("/{document_id}/detail", response_model=DocumentDetailResponse)
def get_document_detail_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> DocumentDetailResponse:
    document = get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    llm_result = repository.get_llm_parse_result(document_id)
    parse_result = repository.get_parse_result(document_id)
    return present_document_detail(
        document=document,
        llm_result=llm_result,
        parse_result=parse_result,
    )


@router.patch("/{document_id}/starred", response_model=DocumentDetailResponse)
def update_document_starred_endpoint(
    document_id: str,
    payload: DocumentStarredRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> DocumentDetailResponse:
    document = get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    document.starred = bool(payload.starred)
    repository.save(document)
    return present_document_detail(
        document=document,
        llm_result=repository.get_llm_parse_result(document.id),
        parse_result=repository.get_parse_result(document.id),
    )


@router.get("/{document_id}/file")
def get_document_file_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    settings: Settings = Depends(settings_dependency),
    current_user: User = Depends(current_user_dependency),
) -> FileResponse:
    document = get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    file_path = resolve_file_path_from_uri(document.blob_uri, settings.object_store_root)
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
    settings: Settings = Depends(settings_dependency),
    current_user: User = Depends(current_user_dependency),
) -> None:
    document = get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    blob_path = resolve_blob_path_from_uri(document.blob_uri, settings.object_store_root)
    metadata_paths = metadata_paths_for_blob_path(blob_path) if blob_path is not None else []

    storage.delete(document.blob_uri)
    for metadata_path in metadata_paths:
        delete_local_path_if_present(metadata_path)

    if blob_path is not None:
        cleanup_empty_storage_dirs(blob_path.parent, settings.object_store_root)

    delete_document(document_id=document.id, repository=repository)


@router.post("/{document_id}/reprocess", response_model=CreateDocumentResponse)
def reprocess_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    dispatcher: IngestionDispatcher = Depends(ingestion_dispatcher_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CreateDocumentResponse:
    document = get_owned_document_or_404(
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
    document = get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    _set_document_status(
        document=document,
        repository=repository,
        status_value=DocumentStatus.PROCESSING,
    )
    ocr_provider = resolve_owner_ocr_provider(repository, current_user.id)
    ocr_auto_switch = resolve_owner_ocr_auto_switch(repository, current_user.id)
    ocr_llm_provider: LLMProvider | None = None
    try:
        ocr_llm_provider = resolve_http_ocr_llm_provider_for_user(
            repository=repository,
            user_id=current_user.id,
            provider_override=provider_override,
            ocr_provider=ocr_provider,
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
    return present_parse_result(result)


@router.get("/{document_id}/parse", response_model=ParseResultResponse)
def get_parse_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> ParseResultResponse:
    get_owned_document_or_404(
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
    return present_parse_result(result)


@router.post("/{document_id}/llm-parse", response_model=LLMParseResultResponse)
def llm_parse_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    provider_override: LLMProvider | None = Depends(llm_provider_dependency),
    settings: Settings = Depends(settings_dependency),
    current_user: User = Depends(current_user_dependency),
) -> LLMParseResultResponse:
    document = get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    llm_provider = resolve_http_metadata_llm_provider_for_user(
        repository=repository,
        user_id=current_user.id,
        provider_override=provider_override,
    )
    ocr_provider = resolve_owner_ocr_provider(repository, current_user.id)
    ocr_auto_switch = resolve_owner_ocr_auto_switch(repository, current_user.id)
    ocr_llm_provider = resolve_http_ocr_llm_provider_for_user(
        repository=repository,
        user_id=current_user.id,
        provider_override=provider_override,
        ocr_provider=ocr_provider,
    )
    try:
        pipeline_result = process_document(
            document=document,
            repository=repository,
            object_store_root=settings.object_store_root,
            metadata_llm_provider=llm_provider,
            ocr_provider=ocr_provider,
            ocr_llm_provider=ocr_llm_provider,
            ocr_auto_switch=ocr_auto_switch,
            actor_type=HistoryActorType.USER,
            actor_id=current_user.id,
            history_source="api.llm_parse",
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return present_llm_parse_result(pipeline_result.llm_result)


@router.get("/{document_id}/llm-parse", response_model=LLMParseResultResponse)
def get_llm_parse_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> LLMParseResultResponse:
    get_owned_document_or_404(
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
    return present_llm_parse_result(result)


@router.patch("/{document_id}/metadata", response_model=LLMParseResultResponse)
def update_document_metadata_endpoint(
    document_id: str,
    payload: MetadataUpdateRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> LLMParseResultResponse:
    document = get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )

    result = update_document_metadata(
        document=document,
        repository=repository,
        suggested_title=payload.suggested_title,
        document_date=payload.document_date,
        correspondent=payload.correspondent,
        document_type=payload.document_type,
        tags=payload.tags,
        actor_type=HistoryActorType.USER,
        actor_id=current_user.id,
        history_source="api.patch_metadata",
    )
    return present_llm_parse_result(result)


@router.get("/{document_id}/history", response_model=list[DocumentHistoryEventResponse])
def list_document_history_endpoint(
    document_id: str,
    limit: int = Query(100, ge=1, le=500),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[DocumentHistoryEventResponse]:
    get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    return [
        present_document_history_event(event)
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
