from datetime import UTC, datetime
from difflib import SequenceMatcher

from zapis.application.interfaces import DocumentRepository, LLMProvider
from zapis.domain.models import Document, LLMParseResult, ParseResult


def _normalize_name(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return " ".join(cleaned.split())


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
    return candidate.strip(), True


def _resolve_tags(candidates: list[str], existing: list[str]) -> tuple[list[str], list[str]]:
    resolved: list[str] = []
    created: list[str] = []
    seen: set[str] = set()

    for tag in candidates:
        resolved_tag, is_new = _resolve_name(tag, existing + resolved)
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
) -> LLMParseResult:
    correspondents = repository.list_correspondents()
    document_types = repository.list_document_types()
    tags = repository.list_tags()

    raw = llm_provider.suggest_metadata(
        filename=document.filename,
        text_preview=parse_result.text_preview,
        existing_correspondents=correspondents,
        existing_document_types=document_types,
        existing_tags=tags,
    )

    candidate_correspondent = str(raw.get("correspondent", "Unknown Sender"))
    candidate_document_type = str(raw.get("document_type", "General Document"))
    candidate_tags = [str(t) for t in raw.get("tags", []) if str(t).strip()]

    correspondent, created_correspondent = _resolve_name(candidate_correspondent, correspondents)
    document_type, created_document_type = _resolve_name(candidate_document_type, document_types)
    resolved_tags, created_tags = _resolve_tags(candidate_tags, tags)

    if created_correspondent:
        repository.add_correspondent(correspondent)
    if created_document_type:
        repository.add_document_type(document_type)
    if created_tags:
        repository.add_tags(created_tags)

    result = LLMParseResult(
        document_id=document.id,
        suggested_title=str(raw.get("suggested_title", document.filename)).strip() or document.filename,
        document_date=_validate_date(raw.get("document_date") if isinstance(raw.get("document_date"), str) else None),
        correspondent=correspondent,
        document_type=document_type,
        tags=resolved_tags,
        created_correspondent=created_correspondent,
        created_document_type=created_document_type,
        created_tags=created_tags,
        created_at=datetime.now(UTC),
    )
    repository.save_llm_parse_result(result)
    return result

