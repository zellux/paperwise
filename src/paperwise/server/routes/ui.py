from pathlib import Path
from html import escape
import json
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse

from paperwise.application.interfaces import DocumentRepository
from paperwise.domain.models import DocumentHistoryEvent, DocumentStatus, LLMParseResult, User
from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    optional_current_user_dependency,
)
from paperwise.server.routes.documents import (
    _document_sort_key,
    _get_owned_document_or_404,
    _iter_filtered_documents,
    _normalized_sort_direction,
    _normalized_sort_field,
    _normalized_values,
)
from paperwise.server.routes.query import _migrate_legacy_chat_threads

router = APIRouter(tags=["ui"])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_VIEW_ARTICLE_RE = re.compile(
    r"\n\s*<article id=\"(?P<view_id>section-[^\"]+)\"(?P<attrs>[^>]*)>.*?\n\s*</article>",
    re.DOTALL,
)
_TABLE_BODY_RE_TEMPLATE = (
    r'(<tbody id="{element_id}"[^>]*>)'
    r'.*?'
    r'(</tbody>)'
)
_ACTIVITY_TOKEN_RE = re.compile(
    r'(<p id="activityTokenTotal" class="activity-token-total">)'
    r'.*?'
    r"(</p>)",
    re.DOTALL,
)
_NAV_LINK_RE = re.compile(
    r'(<a\b(?=[^>]*\bclass="(?P<class>[^"]*\bnav-link\b[^"]*)")'
    r'(?=[^>]*\bhref="(?P<href>[^"]+)")[^>]*>)',
    re.DOTALL,
)
_SEARCH_SUBSECTION_IDS = ("search-section-keyword", "search-section-ask")
_ACTIVE_NAV_BY_VIEW = {
    "section-docs": "/ui/documents",
    "section-document": "/ui/documents",
    "section-search": "/ui/search",
    "section-tags": "/ui/tags",
    "section-document-types": "/ui/document-types",
    "section-pending": "/ui/pending",
    "section-upload": "/ui/upload",
    "section-activity": "/ui/activity",
    "section-settings": "/ui/settings",
}
_PAGE_SCRIPTS_BY_VIEW = {
    "section-docs": ["documents.js"],
    "section-document": ["document.js"],
    "section-search": ["search.js"],
    "section-tags": ["catalog.js"],
    "section-document-types": ["catalog.js"],
    "section-pending": ["pending.js"],
    "section-upload": ["upload.js"],
    "section-settings": ["settings.js"],
}


def _page_initial_data(
    current_user: User | None,
    repository: DocumentRepository | None = None,
) -> dict:
    initial_data: dict = {"authenticated": current_user is not None}
    if current_user is None:
        return initial_data
    initial_data["current_user"] = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
    }
    if repository is not None:
        preference = repository.get_user_preference(current_user.id)
        initial_data["user_preferences"] = preference.preferences if preference is not None else {}
    return initial_data


def _title_case_taxonomy_value(value: str) -> str:
    cleaned = " ".join(str(value or "").strip().split())
    if not cleaned:
        return cleaned
    words: list[str] = []
    for word in cleaned.split(" "):
        letters = "".join(ch for ch in word if ch.isalpha())
        if len(letters) >= 2 and letters.isupper():
            words.append(word)
        elif word.islower():
            words.append(word[:1].upper() + word[1:] if word else word)
        else:
            words.append(word)
    return " ".join(words)


def _document_list_item(repository: DocumentRepository, document_id: str) -> dict | None:
    document = repository.get(document_id)
    if document is None:
        return None
    llm_result = repository.get_llm_parse_result(document.id)
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


def _owner_llm_results(repository: DocumentRepository, current_user: User) -> list[LLMParseResult]:
    results: list[LLMParseResult] = []
    for document in repository.list_documents(limit=10_000):
        if document.owner_id != current_user.id:
            continue
        llm_result = repository.get_llm_parse_result(document.id)
        if llm_result is not None:
            results.append(llm_result)
    return results


def _tag_stats_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = _page_initial_data(current_user, repository)
    if current_user is None:
        return {**initial_data, "tag_stats": []}
    counts: dict[str, int] = {}
    display_name_by_key: dict[str, str] = {}
    for llm_result in _owner_llm_results(repository, current_user):
        seen_tags: set[str] = set()
        for tag in llm_result.tags:
            cleaned = str(tag).strip()
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen_tags:
                continue
            seen_tags.add(key)
            display_name_by_key.setdefault(key, _title_case_taxonomy_value(cleaned))
            counts[key] = counts.get(key, 0) + 1
    return {
        **initial_data,
        "tag_stats": [
            {"tag": display_name_by_key[key], "document_count": count}
            for key, count in sorted(
                counts.items(),
                key=lambda item: (-item[1], display_name_by_key[item[0]].casefold()),
            )
        ],
    }


def _document_type_stats_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = _page_initial_data(current_user, repository)
    if current_user is None:
        return {**initial_data, "document_type_stats": []}
    counts: dict[str, int] = {}
    display_name_by_key: dict[str, str] = {}
    for llm_result in _owner_llm_results(repository, current_user):
        cleaned = str(llm_result.document_type).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        display_name_by_key.setdefault(key, _title_case_taxonomy_value(cleaned))
        counts[key] = counts.get(key, 0) + 1
    return {
        **initial_data,
        "document_type_stats": [
            {"document_type": display_name_by_key[key], "document_count": count}
            for key, count in sorted(
                counts.items(),
                key=lambda item: (-item[1], display_name_by_key[item[0]].casefold()),
            )
        ],
    }


def _activity_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = _page_initial_data(current_user, repository)
    if current_user is None:
        return {**initial_data, "activity_documents": [], "activity_total_tokens": 0}
    ready_documents = [
        document
        for document in repository.list_documents(limit=20)
        if document.owner_id == current_user.id and document.status == DocumentStatus.READY
    ]
    preference = repository.get_user_preference(current_user.id)
    total_tokens = 0
    if preference is not None:
        total_tokens = int(preference.preferences.get("llm_total_tokens_processed") or 0)
    return {
        **initial_data,
        "activity_documents": [
            item
            for item in (_document_list_item(repository, document.id) for document in ready_documents)
            if item is not None
        ],
        "activity_total_tokens": total_tokens,
    }


def _activity_partial_data(
    repository: DocumentRepository,
    current_user: User,
    *,
    limit: int = 20,
) -> dict:
    initial_data = _page_initial_data(current_user, repository)
    normalized_limit = min(100, max(1, int(limit or 20)))
    ready_documents = [
        document
        for document in repository.list_documents(limit=10_000)
        if document.owner_id == current_user.id and document.status == DocumentStatus.READY
    ][:normalized_limit]
    preference = repository.get_user_preference(current_user.id)
    total_tokens = 0
    if preference is not None:
        total_tokens = int(preference.preferences.get("llm_total_tokens_processed") or 0)
    return {
        **initial_data,
        "activity_documents": [
            item
            for item in (_document_list_item(repository, document.id) for document in ready_documents)
            if item is not None
        ],
        "activity_total_tokens": total_tokens,
    }


def _documents_initial_data(
    repository: DocumentRepository,
    current_user: User | None,
    *,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    q: str | None = None,
    tag: list[str] | None = None,
    correspondent: list[str] | None = None,
    document_type: list[str] | None = None,
    status: list[str] | None = None,
) -> dict:
    initial_data = _page_initial_data(current_user, repository)
    normalized_page = max(1, int(page or 1))
    normalized_page_size = min(100, max(1, int(page_size or 20)))
    if current_user is None:
        return {
            **initial_data,
            "documents": [],
            "documents_total": 0,
            "documents_processing_count": 0,
            "documents_page": normalized_page,
            "documents_page_size": normalized_page_size,
        }

    normalized_statuses = _normalized_values(status)
    if not normalized_statuses:
        normalized_statuses = {"ready"}
    matching_documents = list(
        _iter_filtered_documents(
            repository=repository,
            current_user=current_user,
            query=q,
            normalized_tags=_normalized_values(tag),
            normalized_correspondents=_normalized_values(correspondent),
            normalized_document_types=_normalized_values(document_type),
            normalized_statuses=normalized_statuses,
        )
    )
    normalized_sort_field = _normalized_sort_field(sort_by)
    normalized_sort_direction = _normalized_sort_direction(sort_dir)
    if normalized_sort_field and normalized_sort_direction:
        matching_documents.sort(
            key=lambda item: _document_sort_key(item[0], item[1], normalized_sort_field),
            reverse=normalized_sort_direction == "desc",
        )
    offset = (normalized_page - 1) * normalized_page_size
    processing_count = sum(
        1
        for document in repository.list_documents(limit=10_000)
        if document.owner_id == current_user.id and document.status != DocumentStatus.READY
    )
    return {
        **initial_data,
        "documents": [
            item
            for item in (
                _document_list_item(repository, document.id)
                for document, _llm_result in matching_documents[offset : offset + normalized_page_size]
            )
            if item is not None
        ],
        "documents_total": len(matching_documents),
        "documents_processing_count": processing_count,
        "documents_page": normalized_page,
        "documents_page_size": normalized_page_size,
    }


def _pending_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = _page_initial_data(current_user, repository)
    if current_user is None:
        return {**initial_data, "pending_documents": []}
    pending_documents = [
        document
        for document in repository.list_documents(limit=200)
        if document.owner_id == current_user.id and document.status != DocumentStatus.READY
    ]
    return {
        **initial_data,
        "pending_documents": [
            item
            for item in (_document_list_item(repository, document.id) for document in pending_documents)
            if item is not None
        ],
    }


def _document_detail_initial_data(
    repository: DocumentRepository,
    current_user: User | None,
    document_id: str | None,
) -> dict:
    initial_data = _page_initial_data(current_user, repository)
    if current_user is None or not document_id:
        return {**initial_data, "document_detail": None, "document_history": []}
    document = _get_owned_document_or_404(
        document_id=document_id,
        repository=repository,
        current_user=current_user,
    )
    parse_result = repository.get_parse_result(document.id)
    item = _document_list_item(repository, document.id)
    if item is None:
        return {**initial_data, "document_detail": None, "document_history": []}
    return {
        **initial_data,
        "document_detail": {
            "document": item,
            "ocr_text_preview": parse_result.text_preview if parse_result is not None else None,
            "ocr_parsed_at": parse_result.created_at.isoformat() if parse_result is not None else None,
        },
        "document_history": [
            _history_event_item(event)
            for event in repository.list_history(document_id=document.id, limit=100)
        ],
    }


def _replace_table_body(html: str, element_id: str, rows_html: str) -> str:
    pattern = re.compile(_TABLE_BODY_RE_TEMPLATE.format(element_id=re.escape(element_id)), re.DOTALL)
    return pattern.sub(rf"\1\n{rows_html}\n              \2", html, count=1)


def _replace_element_text(html: str, element_id: str, value: str) -> str:
    pattern = re.compile(
        rf'(<(?P<tag>[a-z0-9]+)\b[^>]*\bid="{re.escape(element_id)}"[^>]*>).*?(</(?P=tag)>)',
        re.DOTALL | re.IGNORECASE,
    )
    escaped_value = escape(value)
    return pattern.sub(lambda match: f"{match.group(1)}{escaped_value}{match.group(3)}", html, count=1)


def _replace_element_html(html: str, element_id: str, value: str) -> str:
    pattern = re.compile(
        rf'(<(?P<tag>[a-z0-9]+)\b[^>]*\bid="{re.escape(element_id)}"[^>]*>).*?(</(?P=tag)>)',
        re.DOTALL | re.IGNORECASE,
    )
    return pattern.sub(lambda match: f"{match.group(1)}{value}{match.group(3)}", html, count=1)


def _replace_input_value(html: str, element_id: str, value: str) -> str:
    pattern = re.compile(
        rf'(<input\b(?=[^>]*\bid="{re.escape(element_id)}")[^>]*)(\s*/?>)',
        re.DOTALL | re.IGNORECASE,
    )
    escaped_value = escape(value, quote=True)

    def replace(match: re.Match[str]) -> str:
        start = re.sub(r'\svalue="[^"]*"', "", match.group(1), count=1)
        return f'{start} value="{escaped_value}"{match.group(2)}'

    return pattern.sub(replace, html, count=1)


def _sort_stat_rows(items: list[dict], *, sort_by: str | None, sort_dir: str | None) -> list[dict]:
    field = str(sort_by or "").strip()
    direction = str(sort_dir or "").strip().lower()
    if direction not in {"asc", "desc"}:
        return items
    if field not in {"tag", "document_type", "document_count"}:
        return items
    return sorted(
        items,
        key=lambda item: (
            item.get(field, "") if field == "document_count" else str(item.get(field, "")).casefold()
        ),
        reverse=direction == "desc",
    )


def _tag_rows_html(tag_stats: list[dict]) -> str:
    if not tag_stats:
        return '                <tr><td colspan="3">No tags found.</td></tr>'
    rows: list[str] = []
    for stat in tag_stats:
        raw_tag = str(stat.get("tag") or "")
        tag = escape(raw_tag)
        tag_query = quote(raw_tag, safe="")
        count = int(stat.get("document_count") or 0)
        rows.append(
            "                <tr>"
            f'<td data-label="Tag">{tag}</td>'
            f'<td data-label="Documents">{count}</td>'
            '<td data-label="Action"><div class="table-actions">'
            f'<a class="btn" href="/ui/documents?tag={tag_query}" title="View documents for tag {tag}">'
            "View Docs"
            "</a>"
            "</div></td>"
            "</tr>"
        )
    return "\n".join(rows)


def _document_type_rows_html(type_stats: list[dict]) -> str:
    if not type_stats:
        return '                <tr><td colspan="3">No document types found.</td></tr>'
    rows: list[str] = []
    for stat in type_stats:
        raw_document_type = str(stat.get("document_type") or "")
        document_type = escape(raw_document_type)
        document_type_query = quote(raw_document_type, safe="")
        count = int(stat.get("document_count") or 0)
        rows.append(
            "                <tr>"
            f'<td data-label="Document Type">{document_type}</td>'
            f'<td data-label="Documents">{count}</td>'
            '<td data-label="Action"><div class="table-actions">'
            f'<a class="btn" href="/ui/documents?document_type={document_type_query}" '
            f'title="View documents for type {document_type}">'
            "View Docs"
            "</a>"
            "</div></td>"
            "</tr>"
        )
    return "\n".join(rows)


def _document_title(item: dict) -> str:
    metadata = item.get("llm_metadata")
    if isinstance(metadata, dict):
        title = str(metadata.get("suggested_title") or "").strip()
        if title:
            return title
    return str(item.get("filename") or "Untitled document")


def _history_event_item(event: DocumentHistoryEvent) -> dict:
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


def _format_status(value: str) -> str:
    return str(value or "-").replace("_", " ").upper()


def _format_bytes(value: int | None) -> str:
    bytes_value = int(value or 0)
    if bytes_value <= 0:
        return "0 B"
    if bytes_value < 1024:
        return f"{bytes_value} B"
    kb = bytes_value / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"
    mb = kb / 1024
    return f"{mb:.2f} MB"


def _relative_blob_path(blob_uri: str | None) -> str:
    value = str(blob_uri or "").strip()
    if not value:
        return "-"
    if value.startswith("local://"):
        return value.removeprefix("local://")
    return value


def _format_history_event_type(value: str) -> str:
    labels = {
        "metadata_changed": "Metadata changed",
        "tags_added": "Tags added",
        "tags_removed": "Tags removed",
        "file_moved": "File moved",
        "processing_restarted": "Processing restarted",
        "processing_completed": "Processing completed",
        "processing_failed": "Processing failed",
    }
    return labels.get(value, _format_status(value or "update"))


def _format_history_actor(event: dict) -> str:
    if event.get("actor_type") == "user":
        return f"User: {event['actor_id']}" if event.get("actor_id") else "User"
    return "System"


def _stringify_history_value(value: object) -> str:
    if value is None or value == "":
        return "(empty)"
    return str(value)


def _history_change_lines(event: dict) -> list[str]:
    changes = event.get("changes") if isinstance(event.get("changes"), dict) else {}
    event_type = str(event.get("event_type") or "")
    if event_type == "metadata_changed":
        lines: list[str] = []
        for field, values in changes.items():
            field_values = values if isinstance(values, dict) else {}
            before = _stringify_history_value(field_values.get("before"))
            after = _stringify_history_value(field_values.get("after"))
            lines.append(f"{field}: {before} -> {after}")
        return lines
    if event_type == "tags_added":
        tags = changes.get("tags") if isinstance(changes.get("tags"), list) else []
        return [f"Added: {', '.join(str(tag) for tag in tags)}" if tags else "Added tags"]
    if event_type == "tags_removed":
        tags = changes.get("tags") if isinstance(changes.get("tags"), list) else []
        return [f"Removed: {', '.join(str(tag) for tag in tags)}" if tags else "Removed tags"]
    if event_type == "file_moved":
        return [
            f"From: {_relative_blob_path(str(changes.get('from_blob_uri') or ''))}",
            f"To: {_relative_blob_path(str(changes.get('to_blob_uri') or ''))}",
        ]
    if event_type == "processing_restarted":
        status_change = changes.get("status") if isinstance(changes.get("status"), dict) else {}
        before = _stringify_history_value(status_change.get("before"))
        after = _stringify_history_value(status_change.get("after"))
        return [f"Status: {before} -> {after}"]
    if event_type == "processing_failed":
        status_change = changes.get("status") if isinstance(changes.get("status"), dict) else {}
        before = _stringify_history_value(status_change.get("before"))
        after = _stringify_history_value(status_change.get("after"))
        lines = [f"Status: {before} -> {after}"]
        error = changes.get("error") if isinstance(changes.get("error"), dict) else {}
        if error.get("type"):
            lines.append(f"Error type: {_stringify_history_value(error.get('type'))}")
        if error.get("message"):
            lines.append(f"Error: {_stringify_history_value(error.get('message'))}")
        return lines
    if event_type == "processing_completed":
        status_change = changes.get("status") if isinstance(changes.get("status"), dict) else {}
        before = _stringify_history_value(status_change.get("before"))
        after = _stringify_history_value(status_change.get("after"))
        lines = [f"Status: {before} -> {after}"]
        parse = changes.get("parse") if isinstance(changes.get("parse"), dict) else {}
        if parse.get("parser"):
            lines.append(f"OCR parser: {parse['parser']}")
        ocr_process = None
        if isinstance(parse.get("ocr_process"), dict):
            ocr_process = parse["ocr_process"]
        elif isinstance(parse.get("ocr"), dict) and isinstance(parse["ocr"].get("process"), dict):
            ocr_process = parse["ocr"]["process"]
        if ocr_process is not None:
            location = _stringify_history_value(ocr_process.get("location"))
            engine = _stringify_history_value(ocr_process.get("engine"))
            method = _stringify_history_value(ocr_process.get("method"))
            lines.append(f"OCR path: {location} | {engine} | {method}")
            if ocr_process.get("provider"):
                lines.append(f"OCR provider: {ocr_process['provider']}")
            if ocr_process.get("model"):
                lines.append(f"OCR model: {ocr_process['model']}")
            result_size_bytes = ocr_process.get("result_size_bytes")
            if isinstance(result_size_bytes, int | float):
                lines.append(f"OCR result size: {int(result_size_bytes):,} bytes")
        metadata_parse = changes.get("metadata_parse") if isinstance(changes.get("metadata_parse"), dict) else {}
        if metadata_parse.get("provider"):
            lines.append(f"Metadata provider: {metadata_parse['provider']}")
        if metadata_parse.get("model"):
            lines.append(f"Metadata model: {metadata_parse['model']}")
        total_tokens = metadata_parse.get("total_tokens")
        if isinstance(total_tokens, int | float) and total_tokens > 0:
            lines.append(f"Metadata tokens: {int(total_tokens):,}")
        return lines
    try:
        return [json.dumps(changes, ensure_ascii=True)]
    except TypeError:
        return ["Details unavailable"]


def _history_html(events: list[dict]) -> str:
    if not events:
        return '<p class="document-history-empty">No history entries yet.</p>'
    items: list[str] = []
    for event in events:
        event_type = escape(_format_history_event_type(str(event.get("event_type") or "")))
        actor = escape(_format_history_actor(event))
        source = escape(str(event.get("source") or "-"))
        created_at = escape(str(event.get("created_at") or "-"))
        changes = "\n".join(
            f'                <p class="document-history-change">{escape(line)}</p>'
            for line in _history_change_lines(event)
        )
        items.append(
            '              <article class="document-history-item">\n'
            '                <div class="document-history-header">\n'
            f'                  <span class="document-history-type">{event_type}</span>\n'
            f'                  <span class="document-history-meta">{actor} | {source} | {created_at}</span>\n'
            "                </div>\n"
            f'                <div class="document-history-changes">\n{changes}\n                </div>\n'
            "              </article>"
        )
    return "\n".join(items)


def _activity_rows_html(documents: list[dict]) -> str:
    if not documents:
        return '                <tr><td colspan="4">No processed documents.</td></tr>'
    rows: list[str] = []
    for item in documents:
        raw_document_id = str(item.get("id") or "")
        document_id = escape(raw_document_id)
        document_id_query = quote(raw_document_id, safe="")
        title = escape(_document_title(item))
        status_html = _status_badge_html(str(item.get("status") or ""))
        created_at = escape(str(item.get("created_at") or "-"))
        rows.append(
            "                <tr>"
            f'<td data-label="Title"><a class="link-button" href="/ui/document?id={document_id_query}">{title}</a></td>'
            f'<td data-label="Status">{status_html}</td>'
            f'<td data-label="Uploaded">{created_at}</td>'
            '<td data-label="Action"><div class="table-actions">'
            f'<a class="btn" href="/ui/document?id={document_id_query}" title="Open document">'
            "Open"
            "</a>"
            f'<a class="btn btn-muted" href="/documents/{document_id_query}/file" '
            'target="_blank" rel="noopener noreferrer" title="View file">'
            "View"
            "</a>"
            "</div></td>"
            "</tr>"
        )
    return "\n".join(rows)


def _pending_rows_html(documents: list[dict]) -> str:
    if not documents:
        return '                <tr><td colspan="4">No pending documents.</td></tr>'
    rows: list[str] = []
    for item in documents:
        raw_document_id = str(item.get("id") or "")
        document_id = escape(raw_document_id)
        document_id_query = quote(raw_document_id, safe="")
        title = escape(_document_title(item))
        status_html = _status_badge_html(str(item.get("status") or ""))
        created_at = escape(str(item.get("created_at") or "-"))
        rows.append(
            f'                <tr data-pending-doc-id="{document_id}">'
            f'<td data-label="Title"><a class="link-button" href="/ui/document?id={document_id_query}">{title}</a></td>'
            f'<td data-label="Status">{status_html}</td>'
            f'<td data-label="Created">{created_at}</td>'
            '<td data-label="Action"><div class="table-actions">'
            f'<a class="icon-action-button" href="/ui/document?id={document_id_query}" title="Open document">'
            '<span class="icon-action-label">Open</span>'
            "</a>"
            "</div></td>"
            "</tr>"
        )
    return "\n".join(rows)


def _document_rows_html(documents: list[dict]) -> str:
    if not documents:
        return '                <tr><td colspan="7">No documents found.</td></tr>'
    rows: list[str] = []
    for item in documents:
        raw_document_id = str(item.get("id") or "")
        document_id = escape(raw_document_id)
        document_id_query = quote(raw_document_id, safe="")
        title = escape(_document_title(item))
        metadata = item.get("llm_metadata") if isinstance(item.get("llm_metadata"), dict) else {}
        document_type = escape(str(metadata.get("document_type") or "-"))
        correspondent = escape(str(metadata.get("correspondent") or "-"))
        tags = metadata.get("tags") if isinstance(metadata.get("tags"), list) else []
        tags_text = escape(", ".join(str(tag) for tag in tags) if tags else "-")
        document_date = escape(str(metadata.get("document_date") or "-"))
        status_html = _status_badge_html(str(item.get("status") or ""))
        rows.append(
            f'                <tr data-doc-id="{document_id}">'
            f'<td data-label="Title"><a class="link-button" href="/ui/document?id={document_id_query}">{title}</a></td>'
            f'<td data-label="Type">{document_type}</td>'
            f'<td data-label="Correspondent">{correspondent}</td>'
            f'<td data-label="Tags">{tags_text}</td>'
            f'<td data-label="Date">{document_date}</td>'
            f'<td data-label="Status">{status_html}</td>'
            '<td data-label="Action"><div class="table-actions">'
            f'<a class="btn" href="/ui/document?id={document_id_query}" title="Open document">'
            "Open"
            "</a>"
            f'<a class="btn btn-muted" href="/documents/{document_id_query}/file" '
            'target="_blank" rel="noopener noreferrer" title="View file">'
            "View"
            "</a>"
            f'<button class="btn btn-muted" type="button" data-delete-doc-id="{document_id}" '
            f'data-delete-doc-title="{title}" title="Delete document">Delete</button>'
            "</div></td>"
            "</tr>"
        )
    return "\n".join(rows)


def _status_badge_html(status_value: str) -> str:
    status = str(status_value or "").lower()
    label = escape(_format_status(status))
    return f'<span class="status-badge status-{escape(status)}">{label}</span>'


def _document_detail_fragments(initial_data: dict) -> dict:
    detail = initial_data.get("document_detail")
    if not isinstance(detail, dict):
        return {
            "document_id": "",
            "text": {},
            "html": {},
            "inputs": {},
            "history_html": _history_html([]),
            "document_label": "",
            "blob_uri": "",
        }
    document = detail.get("document") if isinstance(detail.get("document"), dict) else {}
    metadata = document.get("llm_metadata") if isinstance(document.get("llm_metadata"), dict) else {}
    tags = metadata.get("tags") if isinstance(metadata.get("tags"), list) else []
    document_id = str(document.get("id") or "")
    size_bytes = int(document.get("size_bytes") or 0)
    history = initial_data.get("document_history") if isinstance(initial_data.get("document_history"), list) else []
    return {
        "document_id": document_id,
        "document_label": str(metadata.get("suggested_title") or document.get("filename") or document_id),
        "blob_uri": str(document.get("blob_uri") or ""),
        "text": {
            "detailDocId": document_id or "-",
            "detailOwnerId": str(document.get("owner_id") or "-"),
            "detailFilename": str(document.get("filename") or "-"),
            "detailCreatedAt": str(document.get("created_at") or "-"),
            "detailOcrParsedAt": str(detail.get("ocr_parsed_at") or "-"),
            "detailContentType": str(document.get("content_type") or "-"),
            "detailSizeBytes": f"{_format_bytes(size_bytes)} ({size_bytes} bytes)",
            "detailChecksum": str(document.get("checksum_sha256") or "-"),
            "detailBlobUri": _relative_blob_path(str(document.get("blob_uri") or "")),
            "detailOcrContent": str(detail.get("ocr_text_preview") or "").strip() or "-",
        },
        "html": {
            "detailStatus": _status_badge_html(str(document.get("status") or "")),
        },
        "inputs": {
            "metaTitle": str(metadata.get("suggested_title") or document.get("filename") or ""),
            "metaDate": str(metadata.get("document_date") or ""),
            "metaCorrespondent": str(metadata.get("correspondent") or ""),
            "metaType": str(metadata.get("document_type") or ""),
            "metaTags": ", ".join(str(tag) for tag in tags),
        },
        "history_html": _history_html(history),
    }


def _render_document_detail_data(html: str, initial_data: dict) -> str:
    fragments = _document_detail_fragments(initial_data)
    if not fragments["document_id"]:
        return html
    for element_id, value in fragments["text"].items():
        html = _replace_element_text(html, element_id, value)
    for element_id, value in fragments["html"].items():
        html = _replace_element_html(html, element_id, value)
    for element_id, value in fragments["inputs"].items():
        html = _replace_input_value(html, element_id, value)

    html = _replace_element_html(html, "documentHistoryList", fragments["history_html"])
    return html


def _render_initial_page_data(html: str, initial_data: dict) -> str:
    html = _render_document_detail_data(html, initial_data)
    if isinstance(initial_data.get("documents"), list):
        html = _replace_table_body(html, "docsTableBody", _document_rows_html(initial_data["documents"]))
        total = int(initial_data.get("documents_total") or 0)
        processing_count = int(initial_data.get("documents_processing_count") or 0)
        page = max(1, int(initial_data.get("documents_page") or 1))
        page_size = max(1, int(initial_data.get("documents_page_size") or 20))
        total_pages = max(1, (total + page_size - 1) // page_size)
        html = re.sub(
            r'(<span id="docsTotalLabel" class="docs-total-label">).*?(</span>)',
            rf"\1Total documents: {total:,}\2",
            html,
            count=1,
        )
        html = re.sub(
            r'(<span id="docsProcessingLabel" class="docs-total-label">).*?(</span>)',
            rf"\1Processing: {processing_count:,}\2",
            html,
            count=1,
        )
        html = re.sub(
            r'(<span id="pageIndicator" class="page-indicator">).*?(</span>)',
            rf"\1Page {min(page, total_pages)} / {total_pages}\2",
            html,
            count=1,
        )
    if isinstance(initial_data.get("tag_stats"), list):
        html = _replace_table_body(html, "tagsTableBody", _tag_rows_html(initial_data["tag_stats"]))
    if isinstance(initial_data.get("document_type_stats"), list):
        html = _replace_table_body(
            html,
            "documentTypesTableBody",
            _document_type_rows_html(initial_data["document_type_stats"]),
        )
    if isinstance(initial_data.get("activity_documents"), list):
        html = _replace_table_body(
            html,
            "processedDocsTableBody",
            _activity_rows_html(initial_data["activity_documents"]),
        )
        total_tokens = int(initial_data.get("activity_total_tokens") or 0)
        html = _ACTIVITY_TOKEN_RE.sub(
            rf"\1LLM tokens processed: {total_tokens:,}\2",
            html,
            count=1,
        )
    if isinstance(initial_data.get("pending_documents"), list):
        html = _replace_table_body(
            html,
            "pendingTableBody",
            _pending_rows_html(initial_data["pending_documents"]),
        )
    return html


def _render_active_nav(html: str, active_href: str) -> str:
    def replace_link(match: re.Match[str]) -> str:
        tag = match.group(0)
        original_classes = match.group("class")
        classes = [class_name for class_name in original_classes.split() if class_name != "active"]
        if match.group("href") == active_href:
            classes.append("active")
        return tag.replace(f'class="{original_classes}"', f'class="{" ".join(classes)}"', 1)

    return _NAV_LINK_RE.sub(replace_link, html)


def _find_balanced_element_end(html: str, start_pos: int, tag_name: str) -> int | None:
    tag_re = re.compile(rf"</?{tag_name}\b[^>]*>", re.IGNORECASE)
    depth = 1
    for match in tag_re.finditer(html, start_pos):
        if match.group(0).startswith("</"):
            depth -= 1
            if depth == 0:
                return match.end()
            continue
        depth += 1
    return None


def _render_active_search_subsection(html: str, active_section_id: str | None) -> str:
    if active_section_id not in _SEARCH_SUBSECTION_IDS:
        return html

    spans: list[tuple[int, int, str]] = []
    for section_id in _SEARCH_SUBSECTION_IDS:
        start_re = re.compile(
            rf'\n\s*<section\b(?=[^>]*\bid="{re.escape(section_id)}")[^>]*>',
            re.IGNORECASE,
        )
        match = start_re.search(html)
        if match is None:
            continue
        end = _find_balanced_element_end(html, match.end(), "section")
        if end is not None:
            spans.append((match.start(), end, section_id))

    for start, end, section_id in sorted(spans, reverse=True):
        if section_id != active_section_id:
            html = html[:start] + html[end:]
            continue
        section_html = html[start:end].replace(" view-hidden", "", 1)
        html = html[:start] + section_html + html[end:]
    return html


def _chat_thread_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    if current_user is None:
        return {**_page_initial_data(current_user, repository), "chat_threads": []}
    _migrate_legacy_chat_threads(repository, current_user)
    return {
        **_page_initial_data(current_user, repository),
        "chat_threads": [
            {
                "id": thread.id,
                "title": thread.title or "Untitled chat",
                "message_count": len(thread.messages),
                "created_at": thread.created_at.isoformat(),
                "updated_at": thread.updated_at.isoformat(),
            }
            for thread in repository.list_chat_threads(current_user.id, 20)
        ]
    }


def _render_ui_page(
    view_id: str,
    *,
    initial_data: dict | None = None,
    active_nav_href: str | None = None,
    active_search_section_id: str | None = None,
) -> HTMLResponse:
    html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    script_names = ["app.js", *_PAGE_SCRIPTS_BY_VIEW.get(view_id, [])]
    asset_version = str(
        max(
            (_STATIC_DIR / "styles.css").stat().st_mtime_ns,
            *[(_STATIC_DIR / script_name).stat().st_mtime_ns for script_name in script_names],
        )
    )
    html = html.replace('/static/styles.css"', f'/static/styles.css?v={asset_version}"')
    html = html.replace('/static/app.js"', f'/static/app.js?v={asset_version}"')
    page_script_tags = "\n".join(
        f'    <script src="/static/{script_name}?v={asset_version}" defer></script>'
        for script_name in script_names[1:]
    )
    if page_script_tags:
        app_script_tag = f'    <script src="/static/app.js?v={asset_version}" defer></script>'
        html = html.replace(app_script_tag, f"{app_script_tag}\n{page_script_tags}", 1)

    def keep_active_view(match: re.Match[str]) -> str:
        if match.group("view_id") != view_id:
            return ""
        return match.group(0).replace(" view-hidden", "", 1)

    html = _VIEW_ARTICLE_RE.sub(keep_active_view, html)
    html = _render_active_search_subsection(html, active_search_section_id)
    html = _render_active_nav(html, active_nav_href or _ACTIVE_NAV_BY_VIEW.get(view_id, "/ui/documents"))
    if initial_data is not None:
        html = _render_initial_page_data(html, initial_data)
        if initial_data.get("authenticated") is True:
            html = html.replace('<html lang="en">', '<html lang="en" class="has-session">', 1)
        payload = json.dumps(initial_data, ensure_ascii=True).replace("</", "<\\/")
        html = html.replace(
            "  </body>",
            f'    <script id="paperwiseInitialData" type="application/json">{payload}</script>\n'
            "  </body>",
        )

    return HTMLResponse(
        html,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui/documents", status_code=307)


@router.get("/ui/documents", include_in_schema=False)
def documents_page(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str | None = Query(None),
    sort_dir: str | None = Query(None),
    q: str | None = Query(None),
    tag: list[str] | None = Query(None),
    correspondent: list[str] | None = Query(None),
    document_type: list[str] | None = Query(None),
    status: list[str] | None = Query(None),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-docs",
        initial_data=_documents_initial_data(
            repository,
            current_user,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_dir=sort_dir,
            q=q,
            tag=tag,
            correspondent=correspondent,
            document_type=document_type,
            status=status,
        ),
    )


@router.get("/ui/document", include_in_schema=False)
def document_page(
    id: str | None = Query(None),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-document",
        initial_data=_document_detail_initial_data(repository, current_user, id),
    )


@router.get("/ui/tags", include_in_schema=False)
def tags_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page("section-tags", initial_data=_tag_stats_initial_data(repository, current_user))


@router.get("/ui/document-types", include_in_schema=False)
def document_types_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-document-types",
        initial_data=_document_type_stats_initial_data(repository, current_user),
    )


@router.get("/ui/search", include_in_schema=False)
def search_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-search",
        initial_data=_page_initial_data(current_user, repository),
        active_search_section_id="search-section-keyword",
    )


@router.get("/ui/grounded-qa", include_in_schema=False)
def grounded_qa_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-search",
        initial_data=_chat_thread_initial_data(repository, current_user),
        active_nav_href="/ui/grounded-qa",
        active_search_section_id="search-section-ask",
    )


@router.get("/ui/pending", include_in_schema=False)
def pending_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page("section-pending", initial_data=_pending_initial_data(repository, current_user))


@router.get("/ui/upload", include_in_schema=False)
def upload_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page("section-upload", initial_data=_page_initial_data(current_user, repository))


@router.get("/ui/activity", include_in_schema=False)
def activity_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page("section-activity", initial_data=_activity_initial_data(repository, current_user))


@router.get("/ui/settings", include_in_schema=False)
def settings_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page("section-settings", initial_data=_page_initial_data(current_user, repository))


@router.get("/ui/settings/account", include_in_schema=False)
def settings_account_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page("section-settings", initial_data=_page_initial_data(current_user, repository))


@router.get("/ui/settings/display", include_in_schema=False)
def settings_display_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page("section-settings", initial_data=_page_initial_data(current_user, repository))


@router.get("/ui/settings/models", include_in_schema=False)
def settings_models_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page("section-settings", initial_data=_page_initial_data(current_user, repository))


@router.get("/ui/partials/documents", include_in_schema=False)
def documents_partial(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str | None = Query(None),
    sort_dir: str | None = Query(None),
    q: str | None = Query(None),
    tag: list[str] | None = Query(None),
    correspondent: list[str] | None = Query(None),
    document_type: list[str] | None = Query(None),
    status: list[str] | None = Query(None),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> JSONResponse:
    data = _documents_initial_data(
        repository,
        current_user,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_dir=sort_dir,
        q=q,
        tag=tag,
        correspondent=correspondent,
        document_type=document_type,
        status=status,
    )
    return JSONResponse(
        {
            "table_body_html": _document_rows_html(data["documents"]),
            "documents": data["documents"],
            "documents_total": data["documents_total"],
            "documents_processing_count": data["documents_processing_count"],
            "documents_page": data["documents_page"],
            "documents_page_size": data["documents_page_size"],
        },
        headers={"Cache-Control": "no-store"},
    )


@router.get("/ui/partials/tags", include_in_schema=False)
def tags_partial(
    sort_by: str | None = Query(None),
    sort_dir: str | None = Query(None),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> JSONResponse:
    data = _tag_stats_initial_data(repository, current_user)
    tag_stats = _sort_stat_rows(data["tag_stats"], sort_by=sort_by, sort_dir=sort_dir)
    return JSONResponse(
        {
            "table_body_html": _tag_rows_html(tag_stats),
            "tag_stats": tag_stats,
        },
        headers={"Cache-Control": "no-store"},
    )


@router.get("/ui/partials/document-types", include_in_schema=False)
def document_types_partial(
    sort_by: str | None = Query(None),
    sort_dir: str | None = Query(None),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> JSONResponse:
    data = _document_type_stats_initial_data(repository, current_user)
    document_type_stats = _sort_stat_rows(data["document_type_stats"], sort_by=sort_by, sort_dir=sort_dir)
    return JSONResponse(
        {
            "table_body_html": _document_type_rows_html(document_type_stats),
            "document_type_stats": document_type_stats,
        },
        headers={"Cache-Control": "no-store"},
    )


@router.get("/ui/partials/pending", include_in_schema=False)
def pending_partial(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> JSONResponse:
    data = _pending_initial_data(repository, current_user)
    return JSONResponse(
        {
            "table_body_html": _pending_rows_html(data["pending_documents"]),
            "pending_documents": data["pending_documents"],
        },
        headers={"Cache-Control": "no-store"},
    )


@router.get("/ui/partials/activity", include_in_schema=False)
def activity_partial(
    limit: int = Query(20, ge=1, le=100),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> JSONResponse:
    data = _activity_partial_data(repository, current_user, limit=limit)
    return JSONResponse(
        {
            "table_body_html": _activity_rows_html(data["activity_documents"]),
            "activity_documents": data["activity_documents"],
            "activity_total_tokens": data["activity_total_tokens"],
        },
        headers={"Cache-Control": "no-store"},
    )


@router.get("/ui/partials/document", include_in_schema=False)
def document_partial(
    id: str = Query(...),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> JSONResponse:
    data = _document_detail_initial_data(repository, current_user, id)
    return JSONResponse(
        _document_detail_fragments(data),
        headers={"Cache-Control": "no-store"},
    )


@router.get("/style-lab", include_in_schema=False)
def style_lab() -> FileResponse:
    return FileResponse(_STATIC_DIR / "style-lab.html")
