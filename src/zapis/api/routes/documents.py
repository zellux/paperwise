from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from zapis.api.dependencies import (
    document_repository_dependency,
    ingestion_dispatcher_dependency,
)
from zapis.application.interfaces import DocumentRepository, IngestionDispatcher
from zapis.application.services.documents import CreateDocumentCommand, create_document, get_document
from zapis.domain.models import Document

router = APIRouter(prefix="/documents", tags=["documents"])


class CreateDocumentRequest(BaseModel):
    filename: str
    owner_id: str


class CreateDocumentResponse(BaseModel):
    id: str
    status: str
    job_id: str


class DocumentResponse(BaseModel):
    id: str
    filename: str
    owner_id: str
    status: str
    created_at: datetime


def _to_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        owner_id=document.owner_id,
        status=document.status.value,
        created_at=document.created_at,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateDocumentResponse,
)
def create_document_endpoint(
    payload: CreateDocumentRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    dispatcher: IngestionDispatcher = Depends(ingestion_dispatcher_dependency),
) -> CreateDocumentResponse:
    document, job_id = create_document(
        CreateDocumentCommand(
            filename=payload.filename,
            owner_id=payload.owner_id,
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

