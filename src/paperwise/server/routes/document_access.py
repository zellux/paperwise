from fastapi import HTTPException, status

from paperwise.application.interfaces import DocumentRepository
from paperwise.application.services.documents import get_document
from paperwise.domain.models import Document, User


def get_owned_document_or_404(
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
