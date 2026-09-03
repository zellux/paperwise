from dataclasses import dataclass

from paperwise.application.interfaces import DocumentRepository, IngestionDispatcher
from paperwise.application.services.chunk_indexing import (
    DOCUMENT_INDEX_VERSION,
    mark_document_index_failed,
    mark_document_index_pending,
)
from paperwise.domain.models import Document, DocumentIndexState, DocumentIndexStatus


@dataclass(frozen=True)
class BatchIndexResult:
    queued_count: int
    skipped_count: int
    failed_count: int
    jobs: dict[str, str]


def document_index_is_current(*, repository: DocumentRepository, document: Document) -> bool:
    state = repository.get_document_index_state(document.id)
    return bool(
        state is not None
        and state.status == DocumentIndexStatus.READY
        and state.index_version == DOCUMENT_INDEX_VERSION
        and state.source_checksum == document.checksum_sha256
    )


def effective_document_index_status(
    *,
    document: Document,
    state: DocumentIndexState | None,
) -> str:
    if state is None:
        return "not_indexed"
    if state.status == DocumentIndexStatus.READY and (
        state.index_version != DOCUMENT_INDEX_VERSION
        or state.source_checksum != document.checksum_sha256
    ):
        return DocumentIndexStatus.STALE.value
    return state.status.value


def queue_document_indexes(
    *,
    repository: DocumentRepository,
    dispatcher: IngestionDispatcher,
    documents: list[Document],
    force: bool = False,
) -> BatchIndexResult:
    queued_count = 0
    skipped_count = 0
    failed_count = 0
    jobs: dict[str, str] = {}
    for document in documents:
        if repository.get_parse_result(document.id) is None:
            skipped_count += 1
            continue
        if not force and document_index_is_current(repository=repository, document=document):
            skipped_count += 1
            continue
        mark_document_index_pending(repository=repository, document=document)
        try:
            jobs[document.id] = dispatcher.enqueue_reindex(document.id)
        except Exception as exc:
            failed_count += 1
            mark_document_index_failed(repository=repository, document=document, error=str(exc))
            continue
        queued_count += 1
    return BatchIndexResult(
        queued_count=queued_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        jobs=jobs,
    )
