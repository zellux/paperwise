from collections.abc import Iterator

from paperwise.application.interfaces import DocumentRepository
from paperwise.application.services.taxonomy import normalize_name
from paperwise.domain.models import Document, LLMParseResult, User

DOCUMENT_SORT_FIELDS = {"title", "document_type", "correspondent", "tags", "document_date", "status"}


def normalized_sort_field(value: str | None) -> str | None:
    normalized = str(value or "").strip()
    if normalized in DOCUMENT_SORT_FIELDS:
        return normalized
    return None


def normalized_sort_direction(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"asc", "desc"}:
        return normalized
    return None


def normalized_values(values: list[str] | None) -> set[str]:
    normalized: set[str] = set()
    for value in values or []:
        for part in value.split(","):
            item = normalize_name(part)
            if item:
                normalized.add(item)
    return normalized


def document_sort_key(
    document: Document,
    llm_result: LLMParseResult | None,
    sort_field: str,
) -> tuple[str, str]:
    primary = normalize_name(_document_sort_value(document, llm_result, sort_field))
    return primary, document.id


def iter_filtered_documents(
    *,
    repository: DocumentRepository,
    current_user: User,
    query: str | None,
    normalized_tags: set[str],
    normalized_correspondents: set[str],
    normalized_document_types: set[str],
    normalized_statuses: set[str],
) -> Iterator[tuple[Document, LLMParseResult | None]]:
    batch_size = 1000
    scan_offset = 0
    while True:
        documents = repository.list_documents(limit=batch_size, offset=scan_offset)
        if not documents:
            break
        for document in documents:
            if document.owner_id != current_user.id:
                continue
            llm_result = repository.get_llm_parse_result(document.id)
            if not _matches_document_filters(
                document=document,
                llm_result=llm_result,
                normalized_tags=normalized_tags,
                normalized_correspondents=normalized_correspondents,
                normalized_document_types=normalized_document_types,
                normalized_statuses=normalized_statuses,
                query=query,
            ):
                continue
            yield document, llm_result
        if len(documents) < batch_size:
            break
        scan_offset += batch_size


def _document_sort_value(document: Document, llm_result: LLMParseResult | None, sort_field: str) -> str:
    if sort_field == "title":
        return llm_result.suggested_title if llm_result and llm_result.suggested_title else document.filename
    if sort_field == "document_type":
        return llm_result.document_type if llm_result else ""
    if sort_field == "correspondent":
        return llm_result.correspondent if llm_result else ""
    if sort_field == "tags":
        return " ".join(llm_result.tags) if llm_result else ""
    if sort_field == "document_date":
        return llm_result.document_date or "" if llm_result else ""
    if sort_field == "status":
        return document.status.value
    return ""


def _matches_text_query(
    *,
    query: str | None,
    document: Document,
    llm_result: LLMParseResult | None,
) -> bool:
    normalized_query = " ".join(str(query or "").strip().casefold().split())
    if not normalized_query:
        return True

    candidates = [document.filename]
    if llm_result is not None:
        candidates.extend(
            [
                llm_result.suggested_title,
                llm_result.correspondent,
                llm_result.document_type,
                llm_result.document_date or "",
                " ".join(llm_result.tags),
            ]
        )

    haystack = " ".join(" ".join(str(value).split()) for value in candidates).casefold()
    return normalized_query in haystack


def _matches_document_filters(
    *,
    document: Document,
    llm_result: LLMParseResult | None,
    normalized_tags: set[str],
    normalized_correspondents: set[str],
    normalized_document_types: set[str],
    normalized_statuses: set[str],
    query: str | None,
) -> bool:
    if normalized_statuses and normalize_name(document.status.value) not in normalized_statuses:
        return False
    if normalized_tags:
        if llm_result is None or not normalized_tags.intersection({normalize_name(item) for item in llm_result.tags}):
            return False
    if normalized_correspondents:
        if llm_result is None or normalize_name(llm_result.correspondent) not in normalized_correspondents:
            return False
    if normalized_document_types:
        if llm_result is None or normalize_name(llm_result.document_type) not in normalized_document_types:
            return False
    if not _matches_text_query(query=query, document=document, llm_result=llm_result):
        return False
    return True
