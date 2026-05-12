from collections.abc import Iterator
from dataclasses import dataclass

from paperwise.application.interfaces import DocumentStore
from paperwise.application.services.taxonomy import normalize_name
from paperwise.domain.models import Document, DocumentStatus, LLMParseResult, User

DOCUMENT_SORT_FIELDS = {"title", "document_type", "correspondent", "tags", "document_date", "size", "status"}


@dataclass(frozen=True)
class FilteredDocumentListing:
    rows: list[tuple[Document, LLMParseResult | None]]
    total: int


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


def list_filtered_documents(
    *,
    repository: DocumentStore,
    current_user: User,
    query: str | None,
    tag: list[str] | None,
    correspondent: list[str] | None,
    document_type: list[str] | None,
    status: list[str] | None,
    starred: bool | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    limit: int,
    offset: int = 0,
) -> FilteredDocumentListing:
    normalized_statuses = normalized_values(status)
    normalized_tags = normalized_values(tag)
    normalized_correspondents = normalized_values(correspondent)
    normalized_document_types = normalized_values(document_type)
    sort_field = normalized_sort_field(sort_by)
    sort_direction = normalized_sort_direction(sort_dir)
    status_filter = _document_statuses_for_filter(normalized_statuses)
    normalized_offset = max(0, int(offset or 0))
    normalized_limit = max(0, int(limit or 0))
    if (
        not normalized_tags
        and not normalized_correspondents
        and not normalized_document_types
        and starred is not True
        and not _normalized_text_query(query)
        and not (sort_field and sort_direction)
    ):
        if status_filter is not None and not status_filter:
            return FilteredDocumentListing(rows=[], total=0)
        statuses = status_filter or set(DocumentStatus)
        return FilteredDocumentListing(
            rows=repository.list_owner_documents_with_llm_results(
                owner_id=current_user.id,
                limit=normalized_limit,
                offset=normalized_offset,
                statuses=statuses,
            ),
            total=repository.count_owner_documents_by_statuses(
                owner_id=current_user.id,
                statuses=statuses,
            ),
        )
    matching_documents = list(
        iter_filtered_documents(
            repository=repository,
            current_user=current_user,
            query=query,
            normalized_tags=normalized_tags,
            normalized_correspondents=normalized_correspondents,
            normalized_document_types=normalized_document_types,
            normalized_statuses=normalized_statuses,
            starred=starred,
        )
    )
    if sort_field and sort_direction:
        matching_documents.sort(
            key=lambda item: document_sort_key(item[0], item[1], sort_field),
            reverse=sort_direction == "desc",
        )
    return FilteredDocumentListing(
        rows=matching_documents[normalized_offset : normalized_offset + normalized_limit],
        total=len(matching_documents),
    )


def count_filtered_documents(
    *,
    repository: DocumentStore,
    current_user: User,
    query: str | None,
    tag: list[str] | None,
    correspondent: list[str] | None,
    document_type: list[str] | None,
    status: list[str] | None,
    starred: bool | None = None,
) -> int:
    return list_filtered_documents(
        repository=repository,
        current_user=current_user,
        query=query,
        tag=tag,
        correspondent=correspondent,
        document_type=document_type,
        status=status,
        starred=starred,
        limit=0,
    ).total


def iter_filtered_documents(
    *,
    repository: DocumentStore,
    current_user: User,
    query: str | None,
    normalized_tags: set[str],
    normalized_correspondents: set[str],
    normalized_document_types: set[str],
    normalized_statuses: set[str],
    starred: bool | None,
) -> Iterator[tuple[Document, LLMParseResult | None]]:
    batch_size = 1000
    scan_offset = 0
    status_filter = _document_statuses_for_filter(normalized_statuses)
    while True:
        documents_with_metadata = repository.list_owner_documents_with_llm_results(
            owner_id=current_user.id,
            limit=batch_size,
            offset=scan_offset,
            statuses=status_filter,
        )
        if not documents_with_metadata:
            break
        for document, llm_result in documents_with_metadata:
            if not _matches_document_filters(
                document=document,
                llm_result=llm_result,
                normalized_tags=normalized_tags,
                normalized_correspondents=normalized_correspondents,
                normalized_document_types=normalized_document_types,
                normalized_statuses=normalized_statuses,
                starred=starred,
                query=query,
            ):
                continue
            yield document, llm_result
        if len(documents_with_metadata) < batch_size:
            break
        scan_offset += batch_size


def _document_statuses_for_filter(normalized_statuses: set[str]) -> set[DocumentStatus] | None:
    if not normalized_statuses:
        return None
    statuses: set[DocumentStatus] = set()
    for status in normalized_statuses:
        try:
            statuses.add(DocumentStatus(status))
        except ValueError:
            continue
    return statuses


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
    if sort_field == "size":
        return f"{int(document.size_bytes or 0):020d}"
    if sort_field == "status":
        return document.status.value
    return ""


def _matches_text_query(
    *,
    query: str | None,
    document: Document,
    llm_result: LLMParseResult | None,
) -> bool:
    normalized_query = _normalized_text_query(query)
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


def _normalized_text_query(query: str | None) -> str:
    return " ".join(str(query or "").strip().casefold().split())


def _matches_document_filters(
    *,
    document: Document,
    llm_result: LLMParseResult | None,
    normalized_tags: set[str],
    normalized_correspondents: set[str],
    normalized_document_types: set[str],
    normalized_statuses: set[str],
    starred: bool | None,
    query: str | None,
) -> bool:
    if starred is True and not document.starred:
        return False
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
