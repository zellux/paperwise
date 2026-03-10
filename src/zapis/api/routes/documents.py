from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from zapis.api.dependencies import (
    document_repository_dependency,
    ingestion_dispatcher_dependency,
    llm_provider_dependency,
    storage_dependency,
)
from zapis.application.interfaces import (
    DocumentRepository,
    IngestionDispatcher,
    LLMProvider,
    StorageProvider,
)
from zapis.application.services.documents import CreateDocumentCommand, create_document, get_document
from zapis.application.services.llm_parsing import parse_with_llm
from zapis.application.services.parsing import parse_document_blob
from zapis.domain.models import Document, DocumentStatus, LLMParseResult, ParseResult

router = APIRouter(prefix="/documents", tags=["documents"])


class CreateDocumentResponse(BaseModel):
    id: str
    status: str
    job_id: str


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


class TaxonomyResponse(BaseModel):
    correspondents: list[str]
    document_types: list[str]
    tags: list[str]


class TagStatResponse(BaseModel):
    tag: str
    document_count: int


class DocumentDetailResponse(BaseModel):
    document: DocumentResponse
    llm_metadata: DocumentListMetadata | None = None


class MetadataUpdateRequest(BaseModel):
    suggested_title: str
    document_date: str | None = None
    correspondent: str
    document_type: str
    tags: list[str]


PENDING_STATUSES = {
    DocumentStatus.RECEIVED,
    DocumentStatus.PARSING,
    DocumentStatus.PARSED,
    DocumentStatus.ENRICHING,
    DocumentStatus.PROCESSING,
}


def _normalize_name(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return " ".join(cleaned.split())


def _to_title_case(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    return cleaned.title()


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
    existing_by_norm = {_normalize_name(tag): tag for tag in existing_tags}
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
    owner_id: str = Form(...),
    file: UploadFile = File(...),
    repository: DocumentRepository = Depends(document_repository_dependency),
    dispatcher: IngestionDispatcher = Depends(ingestion_dispatcher_dependency),
    storage: StorageProvider = Depends(storage_dependency),
) -> CreateDocumentResponse:
    filename = file.filename or "uploaded-document"
    content = file.file.read()
    checksum = sha256(content).hexdigest()
    storage_key = f"documents/{uuid4()}-{Path(filename).name}"
    blob_uri = storage.put(
        key=storage_key,
        data=content,
        content_type=file.content_type or "application/octet-stream",
    )

    document, job_id = create_document(
        CreateDocumentCommand(
            filename=filename,
            owner_id=owner_id,
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
    repository: DocumentRepository = Depends(document_repository_dependency),
) -> list[DocumentListItemResponse]:
    documents = repository.list_documents(limit=limit)
    return [
        _to_list_item_response(
            document=document,
            llm_result=repository.get_llm_parse_result(document.id),
        )
        for document in documents
    ]


@router.get("/pending", response_model=list[DocumentListItemResponse])
def list_pending_documents_endpoint(
    limit: int = 100,
    repository: DocumentRepository = Depends(document_repository_dependency),
) -> list[DocumentListItemResponse]:
    documents = repository.list_documents(limit=limit)
    pending_docs = [document for document in documents if document.status in PENDING_STATUSES]
    return [
        _to_list_item_response(
            document=document,
            llm_result=repository.get_llm_parse_result(document.id),
        )
        for document in pending_docs
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
) -> DocumentResponse:
    document = get_document(document_id=document_id, repository=repository)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return _to_response(document)


@router.get("/{document_id}/detail", response_model=DocumentDetailResponse)
def get_document_detail_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
) -> DocumentDetailResponse:
    document = get_document(document_id=document_id, repository=repository)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    llm_result = repository.get_llm_parse_result(document_id)
    return _to_detail_response(document=document, llm_result=llm_result)


@router.post("/{document_id}/parse", response_model=ParseResultResponse)
def parse_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
) -> ParseResultResponse:
    document = get_document(document_id=document_id, repository=repository)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    _set_document_status(
        document=document,
        repository=repository,
        status_value=DocumentStatus.PARSING,
    )
    try:
        result = parse_document_blob(document_id=document.id, blob_uri=document.blob_uri)
        repository.save_parse_result(result)
    except Exception:
        _set_document_status(
            document=document,
            repository=repository,
            status_value=DocumentStatus.FAILED,
        )
        raise

    _set_document_status(
        document=document,
        repository=repository,
        status_value=DocumentStatus.PARSED,
    )
    return _to_parse_response(result)


@router.get("/{document_id}/parse", response_model=ParseResultResponse)
def get_parse_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
) -> ParseResultResponse:
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
    llm_provider: LLMProvider = Depends(llm_provider_dependency),
) -> LLMParseResultResponse:
    document = get_document(document_id=document_id, repository=repository)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    try:
        parse_result = repository.get_parse_result(document_id)
        if parse_result is None:
            _set_document_status(
                document=document,
                repository=repository,
                status_value=DocumentStatus.PARSING,
            )
            parse_result = parse_document_blob(document_id=document.id, blob_uri=document.blob_uri)
            repository.save_parse_result(parse_result)
            _set_document_status(
                document=document,
                repository=repository,
                status_value=DocumentStatus.PARSED,
            )

        _set_document_status(
            document=document,
            repository=repository,
            status_value=DocumentStatus.ENRICHING,
        )
        result = parse_with_llm(
            document=document,
            parse_result=parse_result,
            repository=repository,
            llm_provider=llm_provider,
        )
    except Exception:
        _set_document_status(
            document=document,
            repository=repository,
            status_value=DocumentStatus.FAILED,
        )
        raise

    _set_document_status(
        document=document,
        repository=repository,
        status_value=DocumentStatus.READY,
    )
    return _to_llm_parse_response(result)


@router.get("/{document_id}/llm-parse", response_model=LLMParseResultResponse)
def get_llm_parse_document_endpoint(
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
) -> LLMParseResultResponse:
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
) -> LLMParseResultResponse:
    document = get_document(document_id=document_id, repository=repository)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
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
    _set_document_status(
        document=document,
        repository=repository,
        status_value=DocumentStatus.READY,
    )
    return _to_llm_parse_response(result)


@router.get("/metadata/taxonomy", response_model=TaxonomyResponse)
def get_taxonomy_endpoint(
    repository: DocumentRepository = Depends(document_repository_dependency),
) -> TaxonomyResponse:
    return TaxonomyResponse(
        correspondents=repository.list_correspondents(),
        document_types=repository.list_document_types(),
        tags=repository.list_tags(),
    )


@router.get("/metadata/tag-stats", response_model=list[TagStatResponse])
def get_tag_stats_endpoint(
    repository: DocumentRepository = Depends(document_repository_dependency),
) -> list[TagStatResponse]:
    return [
        TagStatResponse(tag=tag, document_count=document_count)
        for tag, document_count in repository.list_tag_stats()
    ]
