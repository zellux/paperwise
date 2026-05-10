from datetime import UTC, datetime
from typing import Protocol

from paperwise.application.interfaces import DocumentStore, HistoryRepository, ParseResultRepository, TaxonomyRepository
from paperwise.application.services.history import build_metadata_history_events
from paperwise.application.services.taxonomy import resolve_existing_name, resolve_tags
from paperwise.domain.models import Document, DocumentStatus, HistoryActorType, LLMParseResult


class MetadataUpdateRepository(DocumentStore, ParseResultRepository, TaxonomyRepository, HistoryRepository, Protocol):
    pass


def validate_document_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


def update_document_metadata(
    *,
    document: Document,
    suggested_title: str,
    document_date: str | None,
    correspondent: str,
    document_type: str,
    tags: list[str],
    repository: MetadataUpdateRepository,
    actor_type: HistoryActorType,
    actor_id: str | None,
    history_source: str,
) -> LLMParseResult:
    correspondents = repository.list_correspondents()
    document_types = repository.list_document_types()
    existing_tags = repository.list_tags()

    resolved_correspondent, created_correspondent = resolve_existing_name(
        correspondent,
        correspondents,
        fallback="Unknown Sender",
    )
    resolved_document_type, created_document_type = resolve_existing_name(
        document_type,
        document_types,
        fallback="General Document",
    )
    resolved_tags, created_tags = resolve_tags(tags, existing_tags)

    if created_correspondent:
        repository.add_correspondent(resolved_correspondent)
    if created_document_type:
        repository.add_document_type(resolved_document_type)
    if created_tags:
        repository.add_tags(created_tags)

    previous = repository.get_llm_parse_result(document.id)
    result = LLMParseResult(
        document_id=document.id,
        suggested_title=suggested_title.strip() or document.filename,
        document_date=validate_document_date(document_date),
        correspondent=resolved_correspondent,
        document_type=resolved_document_type,
        tags=resolved_tags,
        created_correspondent=created_correspondent,
        created_document_type=created_document_type,
        created_tags=created_tags,
        created_at=datetime.now(UTC),
    )
    repository.save_llm_parse_result(result)
    repository.append_history_events(
        build_metadata_history_events(
            previous=previous,
            current=result,
            actor_type=actor_type,
            actor_id=actor_id,
            source=history_source,
        )
    )
    document.status = DocumentStatus.READY
    repository.save(document)
    return result
