from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from paperwise.domain.models import (
    DocumentHistoryEvent,
    HistoryActorType,
    HistoryEventType,
    LLMParseResult,
    ParseResult,
)


def _new_event(
    *,
    document_id: str,
    event_type: HistoryEventType,
    actor_type: HistoryActorType,
    actor_id: str | None,
    source: str,
    changes: dict,
) -> DocumentHistoryEvent:
    return DocumentHistoryEvent(
        id=str(uuid4()),
        document_id=document_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        source=source,
        changes=changes,
        created_at=datetime.now(UTC),
    )


def _tag_key(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def build_metadata_history_events(
    *,
    previous: LLMParseResult | None,
    current: LLMParseResult,
    actor_type: HistoryActorType,
    actor_id: str | None,
    source: str,
) -> list[DocumentHistoryEvent]:
    events: list[DocumentHistoryEvent] = []
    metadata_changes: dict[str, dict[str, str | None]] = {}

    fields = ("suggested_title", "document_date", "correspondent", "document_type")
    for field_name in fields:
        before = getattr(previous, field_name) if previous else None
        after = getattr(current, field_name)
        if before != after:
            metadata_changes[field_name] = {"before": before, "after": after}

    if metadata_changes:
        events.append(
            _new_event(
                document_id=current.document_id,
                event_type=HistoryEventType.METADATA_CHANGED,
                actor_type=actor_type,
                actor_id=actor_id,
                source=source,
                changes=metadata_changes,
            )
        )

    before_tags_by_key = {_tag_key(tag): tag for tag in previous.tags} if previous else {}
    after_tags_by_key = {_tag_key(tag): tag for tag in current.tags}
    added = sorted(
        [tag for key, tag in after_tags_by_key.items() if key not in before_tags_by_key],
        key=str.casefold,
    )
    removed = sorted(
        [tag for key, tag in before_tags_by_key.items() if key not in after_tags_by_key],
        key=str.casefold,
    )
    if added:
        events.append(
            _new_event(
                document_id=current.document_id,
                event_type=HistoryEventType.TAGS_ADDED,
                actor_type=actor_type,
                actor_id=actor_id,
                source=source,
                changes={"tags": added},
            )
        )
    if removed:
        events.append(
            _new_event(
                document_id=current.document_id,
                event_type=HistoryEventType.TAGS_REMOVED,
                actor_type=actor_type,
                actor_id=actor_id,
                source=source,
                changes={"tags": removed},
            )
        )
    return events


def build_file_moved_history_event(
    *,
    document_id: str,
    actor_type: HistoryActorType,
    actor_id: str | None,
    source: str,
    from_blob_uri: str,
    to_blob_uri: str,
) -> DocumentHistoryEvent | None:
    if not from_blob_uri or not to_blob_uri or from_blob_uri == to_blob_uri:
        return None
    return _new_event(
        document_id=document_id,
        event_type=HistoryEventType.FILE_MOVED,
        actor_type=actor_type,
        actor_id=actor_id,
        source=source,
        changes={
            "from_blob_uri": from_blob_uri,
            "to_blob_uri": to_blob_uri,
        },
    )


def build_processing_restarted_history_event(
    *,
    document_id: str,
    actor_type: HistoryActorType,
    actor_id: str | None,
    source: str,
    previous_status: str | None,
    current_status: str,
) -> DocumentHistoryEvent:
    return _new_event(
        document_id=document_id,
        event_type=HistoryEventType.PROCESSING_RESTARTED,
        actor_type=actor_type,
        actor_id=actor_id,
        source=source,
        changes={
            "status": {
                "before": previous_status,
                "after": current_status,
            }
        },
    )


def build_processing_completed_history_event(
    *,
    document_id: str,
    actor_type: HistoryActorType,
    actor_id: str | None,
    source: str,
    previous_status: str | None,
    current_status: str,
    parse_result: ParseResult | None = None,
    llm_result: LLMParseResult | None = None,
) -> DocumentHistoryEvent:
    changes: dict[str, object] = {
        "status": {
            "before": previous_status,
            "after": current_status,
        }
    }
    if parse_result is not None:
        parse_summary: dict[str, object] = {
            "parser": parse_result.parser,
            "page_count": parse_result.page_count,
            "text_preview_chars": len(str(parse_result.text_preview or "")),
            "text_preview_bytes": len(str(parse_result.text_preview or "").encode("utf-8")),
            "text_preview_excerpt": " ".join(str(parse_result.text_preview or "").split())[:240],
        }
        if parse_result.ocr_details:
            process_summary = parse_result.ocr_details.get("process")
            if isinstance(process_summary, dict):
                parse_summary["ocr_process"] = process_summary
            parse_summary["ocr"] = parse_result.ocr_details
        changes["parse"] = parse_summary
    if llm_result is not None and isinstance(llm_result.llm_details, dict):
        changes["metadata_parse"] = dict(llm_result.llm_details)
    return _new_event(
        document_id=document_id,
        event_type=HistoryEventType.PROCESSING_COMPLETED,
        actor_type=actor_type,
        actor_id=actor_id,
        source=source,
        changes=changes,
    )
