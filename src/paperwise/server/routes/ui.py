from pathlib import Path
from datetime import UTC, datetime, timedelta
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
from paperwise.application.services.document_listing import (
    document_sort_key,
    iter_filtered_documents,
    normalized_sort_direction,
    normalized_sort_field,
    normalized_values,
)
from paperwise.domain.models import DocumentHistoryEvent, DocumentStatus, LLMParseResult, User
from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    optional_current_user_dependency,
)
from paperwise.server.routes.document_access import get_owned_document_or_404
from paperwise.server.routes.query import _migrate_legacy_chat_threads

router = APIRouter(tags=["ui"])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_STATIC_CSS_DIR = _STATIC_DIR / "css"
_STATIC_JS_DIR = _STATIC_DIR / "js"
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "ui"
_LAYOUT_TEMPLATE = _TEMPLATE_DIR / "layout.html"
_PARTIALS_DIR = _TEMPLATE_DIR / "partials"
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
_PAGE_PARTIAL_BY_NAME = {
    "documents": "documents.html",
    "document": "document.html",
    "search": "search.html",
    "grounded-qa": "grounded_qa.html",
    "tags": "tags.html",
    "document-types": "document_types.html",
    "pending": "pending.html",
    "upload": "upload.html",
    "activity": "activity.html",
    "settings-display": "settings_display.html",
    "settings-account": "settings_account.html",
    "settings-models": "settings_models.html",
}
_PAGE_SCRIPTS_BY_VIEW = {
    "section-docs": ["documents.js"],
    "section-document": ["single-document.js"],
    "section-search": ["search.js"],
    "section-tags": ["catalog.js"],
    "section-document-types": ["catalog.js"],
    "section-pending": ["pending.js"],
    "section-upload": ["upload.js"],
    "section-activity": ["activity.js"],
    "section-settings": ["settings.js"],
}
SUPPORTED_UI_THEMES = ("atlas", "ledger", "moss", "ember", "folio", "forge")
DEFAULT_UI_THEME = "forge"
UI_THEME_STORAGE_KEY = "paperwise.ui.theme"


def _page_initial_data(
    current_user: User | None,
    repository: DocumentRepository | None = None,
) -> dict:
    initial_data: dict = {
        "authenticated": current_user is not None,
        "ui_themes": list(SUPPORTED_UI_THEMES),
        "default_ui_theme": DEFAULT_UI_THEME,
    }
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

    normalized_statuses = normalized_values(status)
    if not normalized_statuses:
        normalized_statuses = {"ready"}
    matching_documents = list(
        iter_filtered_documents(
            repository=repository,
            current_user=current_user,
            query=q,
            normalized_tags=normalized_values(tag),
            normalized_correspondents=normalized_values(correspondent),
            normalized_document_types=normalized_values(document_type),
            normalized_statuses=normalized_statuses,
        )
    )
    sort_field = normalized_sort_field(sort_by)
    sort_direction = normalized_sort_direction(sort_dir)
    if sort_field and sort_direction:
        matching_documents.sort(
            key=lambda item: document_sort_key(item[0], item[1], sort_field),
            reverse=sort_direction == "desc",
        )
    documents_total = len(matching_documents)
    total_pages = max(1, (documents_total + normalized_page_size - 1) // normalized_page_size)
    normalized_page = min(normalized_page, total_pages)
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
        "documents_total": documents_total,
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
    document = get_owned_document_or_404(
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


def _documents_pagination_toolbar_html(
    *,
    total: int,
    processing_count: int,
    page: int,
    page_size: int,
) -> str:
    normalized_total = max(0, int(total or 0))
    normalized_processing_count = max(0, int(processing_count or 0))
    normalized_page_size = max(1, int(page_size or 20))
    total_pages = max(1, (normalized_total + normalized_page_size - 1) // normalized_page_size)
    normalized_page = min(max(1, int(page or 1)), total_pages)
    prev_disabled = " disabled" if normalized_page <= 1 else ""
    next_disabled = " disabled" if normalized_page >= total_pages else ""
    return (
        '            <div class="docs-summary">\n'
        f'              <span id="docsTotalLabel" class="docs-total-label">Total documents: {normalized_total:,}</span>\n'
        f'              <span id="docsProcessingLabel" class="docs-total-label">Processing: {normalized_processing_count:,}</span>\n'
        "            </div>\n"
        '            <div class="pagination-controls">\n'
        f'              <button id="pagePrevBtn" type="button" class="btn btn-muted" '
        f'data-docs-page-action="prev"{prev_disabled}>Prev</button>\n'
        f'              <span id="pageIndicator" class="page-indicator">Page {normalized_page} / {total_pages}</span>\n'
        f'              <button id="pageNextBtn" type="button" class="btn btn-muted" '
        f'data-docs-page-action="next"{next_disabled}>Next</button>\n'
        "            </div>"
    )


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
        html = _replace_element_html(
            html,
            "documentsPaginationToolbar",
            _documents_pagination_toolbar_html(
                total=total,
                processing_count=processing_count,
                page=page,
                page_size=page_size,
            ),
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
    if isinstance(initial_data.get("chat_threads"), list):
        html = _replace_element_html(
            html,
            "searchAskThreadList",
            _chat_thread_list_html(initial_data["chat_threads"]),
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


def _chat_thread_time_label(value: str) -> str:
    try:
        date = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except ValueError:
        return ""
    if date.tzinfo is None:
        date = date.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    if date.date() == now.date():
        elapsed_minutes = max(1, int((now - date.astimezone(UTC)).total_seconds() // 60))
        if elapsed_minutes < 60:
            return f"{elapsed_minutes} min ago"
        return f"{elapsed_minutes // 60} hr ago"
    if date.date() == (now - timedelta(days=1)).date():
        return "Yesterday"
    try:
        return date.strftime("%b %-d")
    except ValueError:
        return date.strftime("%b %d").replace(" 0", " ")


def _chat_thread_bucket(thread: dict) -> str:
    value = str(thread.get("updated_at") or thread.get("created_at") or "")
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "earlier"
    if date.tzinfo is None:
        date = date.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    if date.date() == now.date():
        return "today"
    if date.date() == (now - timedelta(days=1)).date():
        return "yesterday"
    return "earlier"


def _chat_thread_list_html(
    threads: list[dict],
    *,
    active_thread_id: str = "",
    query: str = "",
) -> str:
    normalized_query = str(query or "").strip().casefold()
    filtered_threads = [
        thread
        for thread in threads
        if not normalized_query or normalized_query in str(thread.get("title") or "").casefold()
    ]
    if not filtered_threads:
        message = "No chats match that search." if normalized_query else "No recent chats yet."
        return f'<p class="thread-empty">{escape(message)}</p>'

    sections: list[str] = []
    for bucket, label in (("today", "Today"), ("yesterday", "Yesterday"), ("earlier", "Earlier")):
        items = [thread for thread in filtered_threads if _chat_thread_bucket(thread) == bucket]
        if not items:
            continue
        rows: list[str] = []
        for thread in items:
            raw_thread_id = str(thread.get("id") or "")
            thread_id = escape(raw_thread_id)
            title = escape(str(thread.get("title") or "Untitled chat"))
            updated = _chat_thread_time_label(str(thread.get("updated_at") or thread.get("created_at") or ""))
            count = int(thread.get("message_count") or 0)
            count_label = f"{count} msg" if count == 1 else f"{count} msgs"
            meta = escape(" | ".join(item for item in (updated, count_label) if item))
            active_class = " active" if raw_thread_id == active_thread_id else ""
            rows.append(
                f'<li class="thread-item{active_class}">'
                f'<button type="button" class="thread-button" data-thread-id="{thread_id}">'
                f'<span class="thread-title">{title}</span>'
                f'<span class="thread-meta">{meta}</span>'
                "</button>"
                f'<button type="button" class="thread-action" data-delete-thread-id="{thread_id}" '
                f'title="Delete chat" aria-label="Delete {title}">&times;</button>'
                "</li>"
            )
        sections.append(
            '<section class="thread-group">'
            f'<h4 class="thread-group-label">{escape(label)}</h4>'
            f'<ul class="thread-list">{"".join(rows)}</ul>'
            "</section>"
        )
    return "".join(sections)


def _chat_threads_partial_data(
    repository: DocumentRepository,
    current_user: User,
    *,
    active_thread_id: str = "",
    query: str = "",
) -> dict:
    data = _chat_thread_initial_data(repository, current_user)
    threads = data["chat_threads"]
    return {
        "chat_threads": threads,
        "thread_list_html": _chat_thread_list_html(
            threads,
            active_thread_id=active_thread_id,
            query=query,
        ),
    }


def _render_ui_page(
    view_id: str,
    *,
    page_name: str,
    initial_data: dict | None = None,
    active_nav_href: str | None = None,
) -> HTMLResponse:
    partial_name = _PAGE_PARTIAL_BY_NAME[page_name]
    html = _LAYOUT_TEMPLATE.read_text(encoding="utf-8")
    content = (_PARTIALS_DIR / partial_name).read_text(encoding="utf-8").rstrip()
    script_names = ["app.js", *_PAGE_SCRIPTS_BY_VIEW.get(view_id, [])]
    asset_version = str(
        max(
            (_STATIC_CSS_DIR / "styles.css").stat().st_mtime_ns,
            *[(_STATIC_JS_DIR / script_name).stat().st_mtime_ns for script_name in script_names],
        )
    )
    asset_query = f"?v={asset_version}"
    html = html.replace("{{asset_query}}", asset_query)
    html = html.replace("{{ui_theme_storage_key}}", UI_THEME_STORAGE_KEY)
    html = html.replace("{{supported_ui_themes_json}}", json.dumps(list(SUPPORTED_UI_THEMES)))
    html = html.replace("{{default_ui_theme}}", DEFAULT_UI_THEME)
    page_script_tags = "\n".join(
        f'    <script src="/static/js/{script_name}{asset_query}" defer></script>'
        for script_name in script_names[1:]
    )
    html = html.replace("{{page_scripts}}", page_script_tags)
    html = html.replace("{{content}}", content)
    html = _render_active_nav(html, active_nav_href or _ACTIVE_NAV_BY_VIEW.get(view_id, "/ui/documents"))
    initial_data_script = ""
    if initial_data is not None:
        html = _render_initial_page_data(html, initial_data)
        if initial_data.get("authenticated") is True:
            html = html.replace('<html lang="en">', '<html lang="en" class="has-session">', 1)
        payload = json.dumps(initial_data, ensure_ascii=True).replace("</", "<\\/")
        initial_data_script = (
            f'    <script id="paperwiseInitialData" type="application/json">{payload}</script>'
        )
    html = html.replace("{{initial_data_script}}", initial_data_script)

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
        page_name="documents",
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
        page_name="document",
        initial_data=_document_detail_initial_data(repository, current_user, id),
    )


@router.get("/ui/tags", include_in_schema=False)
def tags_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-tags",
        page_name="tags",
        initial_data=_tag_stats_initial_data(repository, current_user),
    )


@router.get("/ui/document-types", include_in_schema=False)
def document_types_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-document-types",
        page_name="document-types",
        initial_data=_document_type_stats_initial_data(repository, current_user),
    )


@router.get("/ui/search", include_in_schema=False)
def search_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-search",
        page_name="search",
        initial_data=_page_initial_data(current_user, repository),
    )


@router.get("/ui/grounded-qa", include_in_schema=False)
def grounded_qa_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-search",
        page_name="grounded-qa",
        initial_data=_chat_thread_initial_data(repository, current_user),
        active_nav_href="/ui/grounded-qa",
    )


@router.get("/ui/pending", include_in_schema=False)
def pending_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-pending",
        page_name="pending",
        initial_data=_pending_initial_data(repository, current_user),
    )


@router.get("/ui/upload", include_in_schema=False)
def upload_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-upload",
        page_name="upload",
        initial_data=_page_initial_data(current_user, repository),
    )


@router.get("/ui/activity", include_in_schema=False)
def activity_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-activity",
        page_name="activity",
        initial_data=_activity_initial_data(repository, current_user),
    )


@router.get("/ui/settings", include_in_schema=False)
def settings_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-settings",
        page_name="settings-display",
        initial_data=_page_initial_data(current_user, repository),
    )


@router.get("/ui/settings/account", include_in_schema=False)
def settings_account_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-settings",
        page_name="settings-account",
        initial_data=_page_initial_data(current_user, repository),
    )


@router.get("/ui/settings/display", include_in_schema=False)
def settings_display_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-settings",
        page_name="settings-display",
        initial_data=_page_initial_data(current_user, repository),
    )


@router.get("/ui/settings/models", include_in_schema=False)
def settings_models_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-settings",
        page_name="settings-models",
        initial_data=_page_initial_data(current_user, repository),
    )


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
            "pagination_toolbar_html": _documents_pagination_toolbar_html(
                total=data["documents_total"],
                processing_count=data["documents_processing_count"],
                page=data["documents_page"],
                page_size=data["documents_page_size"],
            ),
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


@router.get("/ui/partials/chat-threads", include_in_schema=False)
def chat_threads_partial(
    active_thread_id: str = Query(""),
    q: str = Query(""),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> JSONResponse:
    return JSONResponse(
        _chat_threads_partial_data(
            repository,
            current_user,
            active_thread_id=active_thread_id,
            query=q,
        ),
        headers={"Cache-Control": "no-store"},
    )


@router.get("/style-lab", include_in_schema=False)
def style_lab() -> FileResponse:
    return FileResponse(_STATIC_DIR / "style-lab.html")
