from dataclasses import dataclass
from pathlib import Path

from paperwise.application.interfaces import DocumentRepository, LLMProvider
from paperwise.application.services.chunk_indexing import index_document_chunks
from paperwise.application.services.file_relocation import move_blob_to_processed
from paperwise.application.services.history import (
    build_file_moved_history_event,
    build_processing_completed_history_event,
)
from paperwise.application.services.llm_parsing import parse_with_llm
from paperwise.application.services.parsing import parse_document_blob
from paperwise.domain.models import Document, DocumentStatus, HistoryActorType, LLMParseResult, ParseResult


@dataclass(frozen=True)
class DocumentPipelineResult:
    parse_result: ParseResult
    llm_result: LLMParseResult
    indexed_chunk_count: int


def process_document(
    *,
    document: Document,
    repository: DocumentRepository,
    object_store_root: Path,
    metadata_llm_provider: LLMProvider,
    ocr_provider: str,
    ocr_llm_provider: LLMProvider | None,
    ocr_auto_switch: bool,
    actor_type: HistoryActorType,
    actor_id: str | None,
    history_source: str,
    parse_blob_uri: str | None = None,
    content_type: str | None = None,
) -> DocumentPipelineResult:
    parse_result = repository.get_parse_result(document.id)
    indexed_chunk_count = 0
    if parse_result is None:
        _set_document_status(
            document=document,
            repository=repository,
            status_value=DocumentStatus.PROCESSING,
        )
        parse_result = parse_document_blob(
            document_id=document.id,
            blob_uri=parse_blob_uri or document.blob_uri,
            content_type=content_type or document.content_type,
            ocr_provider=ocr_provider,
            llm_provider=ocr_llm_provider,
            ocr_auto_switch=ocr_auto_switch,
        )
        repository.save_parse_result(parse_result)
        indexed_chunk_count = index_document_chunks(
            repository=repository,
            document=document,
            parse_result=parse_result,
        )
    else:
        _set_document_status(
            document=document,
            repository=repository,
            status_value=DocumentStatus.PROCESSING,
        )

    llm_result = parse_with_llm(
        document=document,
        parse_result=parse_result,
        repository=repository,
        llm_provider=metadata_llm_provider,
        actor_type=actor_type,
        actor_id=actor_id,
        history_source=history_source,
    )

    previous_blob_uri = document.blob_uri
    previous_status = document.status.value
    document.blob_uri = move_blob_to_processed(
        blob_uri=previous_blob_uri,
        object_store_root=object_store_root,
        document_id=document.id,
        original_filename=document.filename,
        content_type=document.content_type,
        checksum_sha256=document.checksum_sha256,
        size_bytes=document.size_bytes,
    )
    document.status = DocumentStatus.READY
    repository.save(document)
    repository.append_history_events(
        [
            build_processing_completed_history_event(
                document_id=document.id,
                actor_type=actor_type,
                actor_id=actor_id,
                source=history_source,
                previous_status=previous_status,
                current_status=document.status.value,
                parse_result=parse_result,
                llm_result=llm_result,
            )
        ]
    )
    file_move_event = build_file_moved_history_event(
        document_id=document.id,
        actor_type=actor_type,
        actor_id=actor_id,
        source=history_source,
        from_blob_uri=previous_blob_uri,
        to_blob_uri=document.blob_uri,
    )
    if file_move_event is not None:
        repository.append_history_events([file_move_event])
    return DocumentPipelineResult(
        parse_result=parse_result,
        llm_result=llm_result,
        indexed_chunk_count=indexed_chunk_count,
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
