from datetime import UTC, datetime
from difflib import SequenceMatcher

from paperwise.application.interfaces import DocumentRepository, LLMProvider
from paperwise.application.services.history import build_metadata_history_events
from paperwise.domain.models import (
    Document,
    HistoryActorType,
    LLMParseResult,
    ParseResult,
    UserPreference,
)


def _normalize_name(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return " ".join(cleaned.split())


def _to_title_case(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return cleaned

    def looks_like_acronym_token(token: str) -> bool:
        letters = "".join(ch for ch in token if ch.isalpha())
        if not letters or not letters.isalpha():
            return False
        if len(letters) < 2 or len(letters) > 6:
            return False
        vowels = sum(ch in "aeiou" for ch in letters.lower())
        return vowels == 0

    words: list[str] = []
    for word in cleaned.split(" "):
        letters = "".join(ch for ch in word if ch.isalpha())
        if len(letters) >= 2 and letters.isupper():
            words.append(word)
            continue
        if looks_like_acronym_token(word):
            words.append(word.upper())
            continue
        if word.islower():
            words.append(word[:1].upper() + word[1:] if word else word)
            continue
        words.append(word)
    return " ".join(words)


def _resolve_name(candidate: str, existing: list[str]) -> tuple[str, bool]:
    normalized_candidate = _normalize_name(candidate)
    if not normalized_candidate:
        return "Unknown", True

    best_name = ""
    best_score = 0.0
    for name in existing:
        normalized_existing = _normalize_name(name)
        if normalized_existing == normalized_candidate:
            return name, False
        score = SequenceMatcher(None, normalized_candidate, normalized_existing).ratio()
        if score > best_score:
            best_score = score
            best_name = name

    if best_score >= 0.9:
        return best_name, False
    return _to_title_case(candidate), True


def _resolve_tags(candidates: list[str], existing: list[str]) -> tuple[list[str], list[str]]:
    resolved: list[str] = []
    created: list[str] = []
    seen: set[str] = set()

    for tag in candidates:
        resolved_tag, is_new = _resolve_name(tag, existing + resolved)
        resolved_tag = _to_title_case(resolved_tag)
        norm = _normalize_name(resolved_tag)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        resolved.append(resolved_tag)
        if is_new:
            created.append(resolved_tag)
    return resolved, created


def _validate_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        # Keep only YYYY-MM-DD in storage for predictable filtering.
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None


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
        correspondent, created_correspondent = _resolve_name(candidate_correspondent, correspondents)
    elif previous is not None:
        correspondent = previous.correspondent
        created_correspondent = False
    else:
        correspondent = "Unknown Sender"
        created_correspondent = False

    if "document_type" in raw and str(raw.get("document_type") or "").strip():
        candidate_document_type = str(raw.get("document_type", "General Document"))
        document_type, created_document_type = _resolve_name(candidate_document_type, document_types)
    elif previous is not None:
        document_type = previous.document_type
        created_document_type = False
    else:
        document_type = "General Document"
        created_document_type = False

    if "tags" in raw:
        raw_tags = raw.get("tags")
        candidate_tags = [str(t) for t in raw_tags if str(t).strip()] if isinstance(raw_tags, list) else []
        resolved_tags, created_tags = _resolve_tags(candidate_tags, tags)
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
            validated_date = _validate_date(raw_date)
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
    )
    repository.save_llm_parse_result(result)
    if llm_total_tokens > 0:
        preference = repository.get_user_preference(document.owner_id)
        preference_data = dict(preference.preferences) if preference is not None else {}
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
