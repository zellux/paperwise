from dataclasses import dataclass

from paperwise.application.interfaces import DocumentRepository, IngestionDispatcher
from paperwise.application.services.history import build_processing_restarted_history_event
from paperwise.domain.models import Document, DocumentHistoryEvent, DocumentStatus, HistoryActorType, LLMParseResult

PENDING_DOCUMENT_STATUSES = {
    DocumentStatus.RECEIVED,
    DocumentStatus.PROCESSING,
    DocumentStatus.FAILED,
}


@dataclass(frozen=True)
class RestartPendingDocumentsResult:
    restarted_count: int
    skipped_ready_count: int


def list_pending_documents(
    *,
    repository: DocumentRepository,
    owner_id: str,
    limit: int,
) -> list[tuple[Document, LLMParseResult | None]]:
    return repository.list_owner_documents_with_llm_results(
        owner_id=owner_id,
        limit=limit,
        statuses=PENDING_DOCUMENT_STATUSES,
    )


def restart_pending_documents(
    *,
    repository: DocumentRepository,
    dispatcher: IngestionDispatcher,
    owner_id: str,
    actor_id: str | None,
    limit: int,
) -> RestartPendingDocumentsResult:
    documents = [
        document
        for document, _llm_result in repository.list_owner_documents_with_llm_results(
            owner_id=owner_id,
            limit=limit,
        )
    ]
    restarted_count = 0
    skipped_ready_count = 0
    history_events: list[DocumentHistoryEvent] = []

    for document in documents:
        if document.status == DocumentStatus.READY:
            skipped_ready_count += 1
            continue
        previous_status = document.status.value
        document.status = DocumentStatus.PROCESSING
        repository.save(document)
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
                actor_id=actor_id,
                source="api.pending_restart",
                previous_status=previous_status,
                current_status=document.status.value,
            )
        )
        restarted_count += 1

    repository.append_history_events(history_events)
    return RestartPendingDocumentsResult(
        restarted_count=restarted_count,
        skipped_ready_count=skipped_ready_count,
    )
