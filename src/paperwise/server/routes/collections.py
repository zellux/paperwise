from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from paperwise.application.interfaces import DocumentRepository
from paperwise.domain.models import Collection, User
from paperwise.server.dependencies import current_user_dependency, document_repository_dependency

router = APIRouter(prefix="/collections", tags=["collections"])


class CollectionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=2000)


class CollectionResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str
    document_count: int
    created_at: datetime
    updated_at: datetime


class CollectionDocumentsRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list)


class CollectionDocumentIdsResponse(BaseModel):
    collection_id: str
    document_ids: list[str]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)


class SearchHitResponse(BaseModel):
    document_id: str
    title: str
    filename: str
    score: float
    snippet: str
    matched_terms: list[str]
    created_at: datetime
    document_type: str | None = None
    correspondent: str | None = None
    tags: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    total_hits: int
    hits: list[SearchHitResponse]


def _to_collection_response(
    *,
    repository: DocumentRepository,
    collection: Collection,
) -> CollectionResponse:
    document_count = len(repository.list_collection_document_ids(collection.id))
    return CollectionResponse(
        id=collection.id,
        owner_id=collection.owner_id,
        name=collection.name,
        description=collection.description,
        document_count=document_count,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


def _get_collection_or_404(
    *,
    collection_id: str,
    repository: DocumentRepository,
    current_user: User,
) -> Collection:
    collection = repository.get_collection(collection_id)
    if collection is None or collection.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    return collection


def _build_search_response(
    *,
    repository: DocumentRepository,
    query: str,
    hits,
) -> SearchResponse:
    items: list[SearchHitResponse] = []
    for hit in hits:
        llm = repository.get_llm_parse_result(hit.document.id)
        title = llm.suggested_title if llm is not None and llm.suggested_title else hit.document.filename
        items.append(
            SearchHitResponse(
                document_id=hit.document.id,
                title=title,
                filename=hit.document.filename,
                score=hit.score,
                snippet=hit.snippet,
                matched_terms=hit.matched_terms,
                created_at=hit.document.created_at,
                document_type=llm.document_type if llm is not None else None,
                correspondent=llm.correspondent if llm is not None else None,
                tags=list(llm.tags or []) if llm is not None else [],
            )
        )
    return SearchResponse(query=query, total_hits=len(items), hits=items)


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection_endpoint(
    payload: CollectionCreateRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CollectionResponse:
    now = datetime.now(UTC)
    collection = Collection(
        id=str(uuid4()),
        owner_id=current_user.id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        created_at=now,
        updated_at=now,
    )
    repository.create_collection(collection)
    return _to_collection_response(repository=repository, collection=collection)


@router.get("", response_model=list[CollectionResponse])
def list_collections_endpoint(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[CollectionResponse]:
    collections = repository.list_collections(current_user.id)
    return [_to_collection_response(repository=repository, collection=item) for item in collections]


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection_endpoint(
    collection_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CollectionResponse:
    collection = _get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    return _to_collection_response(repository=repository, collection=collection)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection_endpoint(
    collection_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> None:
    _get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    repository.delete_collection(collection_id)


@router.get("/{collection_id}/documents", response_model=CollectionDocumentIdsResponse)
def list_collection_documents_endpoint(
    collection_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CollectionDocumentIdsResponse:
    _get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    return CollectionDocumentIdsResponse(
        collection_id=collection_id,
        document_ids=repository.list_collection_document_ids(collection_id),
    )


@router.post("/{collection_id}/documents", response_model=CollectionDocumentIdsResponse)
def add_collection_documents_endpoint(
    collection_id: str,
    payload: CollectionDocumentsRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CollectionDocumentIdsResponse:
    _get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    document_ids = sorted(set(payload.document_ids))
    for document_id in document_ids:
        document = repository.get(document_id)
        if document is None or document.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document for collection: {document_id}",
            )
    repository.add_collection_documents(
        collection_id=collection_id,
        document_ids=document_ids,
        added_at=datetime.now(UTC),
    )
    return CollectionDocumentIdsResponse(
        collection_id=collection_id,
        document_ids=repository.list_collection_document_ids(collection_id),
    )


@router.delete("/{collection_id}/documents/{document_id}", response_model=CollectionDocumentIdsResponse)
def remove_collection_document_endpoint(
    collection_id: str,
    document_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CollectionDocumentIdsResponse:
    _get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    repository.remove_collection_document(collection_id, document_id)
    return CollectionDocumentIdsResponse(
        collection_id=collection_id,
        document_ids=repository.list_collection_document_ids(collection_id),
    )


@router.post("/search", response_model=SearchResponse)
def search_all_documents_endpoint(
    payload: SearchRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> SearchResponse:
    hits = repository.search_documents(
        owner_id=current_user.id,
        query=payload.query,
        limit=payload.limit,
        document_ids=None,
    )
    return _build_search_response(repository=repository, query=payload.query, hits=hits)


@router.post("/{collection_id}/search", response_model=SearchResponse)
def search_collection_documents_endpoint(
    collection_id: str,
    payload: SearchRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> SearchResponse:
    _get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    scoped_ids = repository.list_collection_document_ids(collection_id)
    hits = repository.search_documents(
        owner_id=current_user.id,
        query=payload.query,
        limit=payload.limit,
        document_ids=scoped_ids,
    )
    return _build_search_response(repository=repository, query=payload.query, hits=hits)
