from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


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


class DocumentListMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    suggested_title: str
    document_date: str | None
    correspondent: str
    document_type: str
    tags: list[str]


class DocumentListItemResponse(DocumentResponse):
    llm_metadata: DocumentListMetadata | None = None


class ParseResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    parser: str
    status: str
    size_bytes: int
    page_count: int
    text_preview: str
    created_at: datetime


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


class DocumentDetailResponse(BaseModel):
    document: DocumentResponse
    llm_metadata: DocumentListMetadata | None = None
    ocr_text_preview: str | None = None
    ocr_parsed_at: datetime | None = None
