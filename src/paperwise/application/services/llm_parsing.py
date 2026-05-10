from datetime import UTC, datetime

from paperwise.application.interfaces import DocumentRepository, LLMProvider
from paperwise.application.services.history import build_metadata_history_events
from paperwise.application.services.llm_runtime import summarize_llm_provider
from paperwise.application.services.metadata_updates import validate_document_date
from paperwise.application.services.taxonomy import resolve_existing_name, resolve_tags
from paperwise.application.services.user_preferences import load_user_preferences
from paperwise.domain.models import (
    Document,
    HistoryActorType,
    LLMParseResult,
    ParseResult,
    UserPreference,
)


def _build_metadata_llm_details(
    *,
    llm_provider: LLMProvider,
    llm_total_tokens: int,
) -> dict[str, object]:
    summary = summarize_llm_provider(llm_provider)
    return {
        "task": "metadata",
        "engine": "llm",
        "provider": summary["provider"],
        "model": summary["model"],
        "base_url": summary["base_url"],
        "total_tokens": llm_total_tokens,
    }


def parse_with_llm(
    *,
    document: Document,
    parse_result: ParseResult,
    repository: DocumentRepository,
    llm_provider: LLMProvider,
    actor_type: HistoryActorType = HistoryActorType.SYSTEM,
    actor_id: str | None = None,
    history_source: str = "service.llm_parse",
) -> LLMParseResult:
    correspondents = repository.list_correspondents()
    document_types = repository.list_document_types()
    tags = repository.list_tags()
    previous = repository.get_llm_parse_result(document.id)

    raw = llm_provider.suggest_metadata(
        filename=document.filename,
        text_preview=parse_result.text_preview,
        current_correspondent=previous.correspondent if previous is not None else None,
        current_document_type=previous.document_type if previous is not None else None,
        existing_correspondents=correspondents,
        existing_document_types=document_types,
        existing_tags=tags,
    )
    raw_total_tokens = raw.get("llm_total_tokens")
    llm_total_tokens = raw_total_tokens if isinstance(raw_total_tokens, int) and raw_total_tokens > 0 else 0

    if "correspondent" in raw and str(raw.get("correspondent") or "").strip():
        candidate_correspondent = str(raw.get("correspondent", "Unknown Sender"))
        correspondent, created_correspondent = resolve_existing_name(
            candidate_correspondent,
            correspondents,
            fallback="Unknown Sender",
            fuzzy_threshold=0.9,
        )
    elif previous is not None:
        correspondent = previous.correspondent
        created_correspondent = False
    else:
        correspondent = "Unknown Sender"
        created_correspondent = False

    if "document_type" in raw and str(raw.get("document_type") or "").strip():
        candidate_document_type = str(raw.get("document_type", "General Document"))
        document_type, created_document_type = resolve_existing_name(
            candidate_document_type,
            document_types,
            fallback="General Document",
            fuzzy_threshold=0.9,
        )
    elif previous is not None:
        document_type = previous.document_type
        created_document_type = False
    else:
        document_type = "General Document"
        created_document_type = False

    if "tags" in raw:
        raw_tags = raw.get("tags")
        candidate_tags = [str(t) for t in raw_tags if str(t).strip()] if isinstance(raw_tags, list) else []
        resolved_tags, created_tags = resolve_tags(candidate_tags, tags, fuzzy_threshold=0.9)
    elif previous is not None:
        resolved_tags = list(previous.tags)
        created_tags = []
    else:
        resolved_tags = []
        created_tags = []

    if created_correspondent:
        repository.add_correspondent(correspondent)
    if created_document_type:
        repository.add_document_type(document_type)
    if created_tags:
        repository.add_tags(created_tags)
    if "suggested_title" in raw and str(raw.get("suggested_title") or "").strip():
        suggested_title = str(raw.get("suggested_title", document.filename)).strip()
    elif previous is not None:
        suggested_title = previous.suggested_title
    else:
        suggested_title = document.filename

    if "document_date" in raw:
        raw_date = raw.get("document_date")
        if isinstance(raw_date, str):
            validated_date = validate_document_date(raw_date)
            if validated_date is not None:
                document_date = validated_date
            elif previous is not None:
                document_date = previous.document_date
            else:
                document_date = None
        elif raw_date is None and previous is not None:
            # Preserve previously known date when provider omits this value.
            document_date = previous.document_date
        else:
            document_date = None
    elif previous is not None:
        document_date = previous.document_date
    else:
        document_date = None

    result = LLMParseResult(
        document_id=document.id,
        suggested_title=suggested_title,
        document_date=document_date,
        correspondent=correspondent,
        document_type=document_type,
        tags=resolved_tags,
        created_correspondent=created_correspondent,
        created_document_type=created_document_type,
        created_tags=created_tags,
        created_at=datetime.now(UTC),
        llm_total_tokens=llm_total_tokens,
        llm_details=_build_metadata_llm_details(
            llm_provider=llm_provider,
            llm_total_tokens=llm_total_tokens,
        ),
    )
    repository.save_llm_parse_result(result)
    if llm_total_tokens > 0:
        preference_data = load_user_preferences(repository=repository, user_id=document.owner_id)
        existing_total = preference_data.get("llm_total_tokens_processed", 0)
        running_total = existing_total if isinstance(existing_total, int) and existing_total >= 0 else 0
        preference_data["llm_total_tokens_processed"] = running_total + llm_total_tokens
        repository.save_user_preference(
            UserPreference(
                user_id=document.owner_id,
                preferences=preference_data,
            )
        )
    events = build_metadata_history_events(
        previous=previous,
        current=result,
        actor_type=actor_type,
        actor_id=actor_id,
        source=history_source,
    )
    repository.append_history_events(events)
    return result
