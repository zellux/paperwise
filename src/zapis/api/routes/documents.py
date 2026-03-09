from datetime import datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from zapis.api.dependencies import (
    document_repository_dependency,
    ingestion_dispatcher_dependency,
    storage_dependency,
)
from zapis.application.interfaces import (
    DocumentRepository,
    IngestionDispatcher,
    StorageProvider,
)
from zapis.application.services.documents import CreateDocumentCommand, create_document, get_document
from zapis.domain.models import Document

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
