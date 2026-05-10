from paperwise.domain.models import Document, DocumentHistoryEvent, LLMParseResult


def document_list_item(document: Document, llm_result: LLMParseResult | None) -> dict:
    metadata = None
    if llm_result is not None:
        metadata = {
            "suggested_title": llm_result.suggested_title,
            "document_date": llm_result.document_date,
            "correspondent": llm_result.correspondent,
            "document_type": llm_result.document_type,
            "tags": list(llm_result.tags),
        }
    return {
        "id": document.id,
        "filename": document.filename,
        "owner_id": document.owner_id,
        "blob_uri": document.blob_uri,
        "checksum_sha256": document.checksum_sha256,
        "content_type": document.content_type,
        "size_bytes": document.size_bytes,
        "status": document.status.value,
        "created_at": document.created_at.isoformat(),
        "llm_metadata": metadata,
    }


def history_event_item(event: DocumentHistoryEvent) -> dict:
    return {
        "id": event.id,
        "document_id": event.document_id,
        "event_type": event.event_type.value,
        "actor_type": event.actor_type.value,
        "actor_id": event.actor_id,
        "source": event.source,
        "changes": event.changes,
        "created_at": event.created_at.isoformat(),
    }
