from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from paperwise.application.interfaces import DocumentRepository, LLMProvider
from paperwise.application.services.grounded_qa import (
    GroundedQATimeoutError,
    answer_grounded_question,
    resolve_metadata_scoped_document_ids,
    search_document_chunks_multi_query,
)
from paperwise.application.services.llm_preferences import LLM_TASK_GROUNDED_QA
from paperwise.domain.models import Collection, User
from paperwise.infrastructure.llm.debug_log import log_llm_exchange
from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    llm_provider_dependency,
)
from paperwise.server.collection_access import get_collection_or_404
from paperwise.server.schemas.collections import (
    AskResponse,
    AskRequest,
    CollectionCreateRequest,
    CollectionDocumentIdsResponse,
    CollectionDocumentsRequest,
    CollectionResponse,
    SearchRequest,
    SearchResponse,
)
from paperwise.server.llm_provider import resolve_http_llm_provider_for_user

router = APIRouter(prefix="/collections", tags=["collections"])


def _log_grounded_qa_exchange(
    provider: str,
    endpoint: str,
    request_payload: dict,
    response_status: int | None,
    response_payload: object,
    error: str | None,
) -> None:
    log_llm_exchange(
        provider=provider,
        endpoint=endpoint,
        request_payload=request_payload,
        response_status=response_status,
        response_payload=response_payload,
        error=error,
    )


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
    return CollectionResponse.from_repository(repository=repository, collection=collection)


@router.get("", response_model=list[CollectionResponse])
def list_collections_endpoint(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[CollectionResponse]:
    collections = repository.list_collections(current_user.id)
    return [CollectionResponse.from_repository(repository=repository, collection=item) for item in collections]


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection_endpoint(
    collection_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> CollectionResponse:
    collection = get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    return CollectionResponse.from_repository(repository=repository, collection=collection)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection_endpoint(
    collection_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> None:
    get_collection_or_404(
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
    get_collection_or_404(
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
    get_collection_or_404(
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
    get_collection_or_404(
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
    scoped_ids = resolve_metadata_scoped_document_ids(
        repository=repository,
        current_user=current_user,
        base_document_ids=None,
        tag_filters=payload.tag,
        document_type_filters=payload.document_type,
    )
    hits = search_document_chunks_multi_query(
        repository=repository,
        owner_id=current_user.id,
        query=payload.query,
        limit=max(payload.limit * 4, payload.limit),
        document_ids=scoped_ids,
    )
    return SearchResponse.from_chunk_hits(
        repository=repository,
        query=payload.query,
        limit=payload.limit,
        hits=hits,
    )


@router.post("/{collection_id}/search", response_model=SearchResponse)
def search_collection_documents_endpoint(
    collection_id: str,
    payload: SearchRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> SearchResponse:
    get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    collection_doc_ids = repository.list_collection_document_ids(collection_id)
    scoped_ids = resolve_metadata_scoped_document_ids(
        repository=repository,
        current_user=current_user,
        base_document_ids=collection_doc_ids,
        tag_filters=payload.tag,
        document_type_filters=payload.document_type,
    )
    hits = search_document_chunks_multi_query(
        repository=repository,
        owner_id=current_user.id,
        query=payload.query,
        limit=max(payload.limit * 4, payload.limit),
        document_ids=scoped_ids,
    )
    return SearchResponse.from_chunk_hits(
        repository=repository,
        query=payload.query,
        limit=payload.limit,
        hits=hits,
    )


@router.post("/ask", response_model=AskResponse)
def ask_all_documents_endpoint(
    payload: AskRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    provider_override: LLMProvider | None = Depends(llm_provider_dependency),
    current_user: User = Depends(current_user_dependency),
) -> AskResponse:
    llm_provider = resolve_http_llm_provider_for_user(
        repository=repository,
        user_id=current_user.id,
        provider_override=provider_override,
        task=LLM_TASK_GROUNDED_QA,
        missing_provider_detail="Configure a Grounded Q&A LLM connection in Settings before asking questions.",
        missing_api_key_detail="Selected Grounded Q&A LLM connection requires an API key in Settings.",
        missing_base_url_detail="Custom Grounded Q&A connection requires a base URL in Settings.",
    )
    scoped_ids = resolve_metadata_scoped_document_ids(
        repository=repository,
        current_user=current_user,
        base_document_ids=None,
        tag_filters=payload.tag,
        document_type_filters=payload.document_type,
    )
    try:
        result = answer_grounded_question(
            repository=repository,
            llm_provider=llm_provider,
            owner_id=current_user.id,
            question=payload.question,
            top_k_chunks=payload.top_k_chunks,
            max_documents=payload.max_documents,
            document_ids=scoped_ids,
            debug_scope={
                "collection_id": None,
                "tag": payload.tag,
                "document_type": payload.document_type,
                "scoped_document_count": len(scoped_ids) if scoped_ids is not None else None,
            },
            debug_enabled=payload.debug,
            log_exchange=_log_grounded_qa_exchange,
        )
    except GroundedQATimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    return AskResponse.from_grounded_qa_result(result)


@router.post("/{collection_id}/ask", response_model=AskResponse)
def ask_collection_documents_endpoint(
    collection_id: str,
    payload: AskRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
    provider_override: LLMProvider | None = Depends(llm_provider_dependency),
    current_user: User = Depends(current_user_dependency),
) -> AskResponse:
    get_collection_or_404(
        collection_id=collection_id,
        repository=repository,
        current_user=current_user,
    )
    llm_provider = resolve_http_llm_provider_for_user(
        repository=repository,
        user_id=current_user.id,
        provider_override=provider_override,
        task=LLM_TASK_GROUNDED_QA,
        missing_provider_detail="Configure a Grounded Q&A LLM connection in Settings before asking questions.",
        missing_api_key_detail="Selected Grounded Q&A LLM connection requires an API key in Settings.",
        missing_base_url_detail="Custom Grounded Q&A connection requires a base URL in Settings.",
    )
    collection_doc_ids = repository.list_collection_document_ids(collection_id)
    scoped_ids = resolve_metadata_scoped_document_ids(
        repository=repository,
        current_user=current_user,
        base_document_ids=collection_doc_ids,
        tag_filters=payload.tag,
        document_type_filters=payload.document_type,
    )
    try:
        result = answer_grounded_question(
            repository=repository,
            llm_provider=llm_provider,
            owner_id=current_user.id,
            question=payload.question,
            top_k_chunks=payload.top_k_chunks,
            max_documents=payload.max_documents,
            document_ids=scoped_ids,
            debug_scope={
                "collection_id": collection_id,
                "tag": payload.tag,
                "document_type": payload.document_type,
                "scoped_document_count": len(scoped_ids) if scoped_ids is not None else None,
            },
            debug_enabled=payload.debug,
            log_exchange=_log_grounded_qa_exchange,
        )
    except GroundedQATimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc)) from exc
    return AskResponse.from_grounded_qa_result(result)
