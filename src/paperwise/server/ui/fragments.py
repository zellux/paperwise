from datetime import UTC, datetime, timedelta
from html import escape
import json
from urllib.parse import quote


def tag_rows_html(tag_stats: list[dict]) -> str:
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


def document_type_rows_html(type_stats: list[dict]) -> str:
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


def activity_rows_html(documents: list[dict]) -> str:
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


def pending_rows_html(documents: list[dict]) -> str:
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


def document_rows_html(documents: list[dict]) -> str:
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
            f'<a class="btn" href="/ui/document?id={document_id_query}" title="View document details">'
            "Details"
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


def documents_pagination_toolbar_html(
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


def _fragment_data_attrs(attrs: dict[str, object]) -> str:
    parts: list[str] = []
    for key, value in attrs.items():
        attr_name = key.replace("_", "-")
        if isinstance(value, bool):
            attr_value = "true" if value else "false"
        else:
            attr_value = str(value)
        parts.append(f'data-{escape(attr_name)}="{escape(attr_value, quote=True)}"')
    return (" " + " ".join(parts)) if parts else ""


def _partial_template(
    target_id: str,
    html: str,
    *,
    attr: str = "data-partial-target",
) -> str:
    return f'<template {attr}="{escape(target_id, quote=True)}">{html}</template>'


def ui_partial_fragment_html(
    *,
    templates: dict[str, str],
    data_attrs: dict[str, object] | None = None,
) -> str:
    body = "\n".join(
        _partial_template(target_id, html) for target_id, html in templates.items()
    )
    return (
        f'<div class="ui-partial-fragment"'
        f"{_fragment_data_attrs(data_attrs or {})}>{body}</div>"
    )


def documents_partial_html(data: dict) -> str:
    documents = data["documents"]
    return ui_partial_fragment_html(
        templates={
            "docsTableBody": document_rows_html(documents),
            "documentsPaginationToolbar": documents_pagination_toolbar_html(
                total=data["documents_total"],
                processing_count=data["documents_processing_count"],
                page=data["documents_page"],
                page_size=data["documents_page_size"],
            ),
        },
        data_attrs={
            "documents_returned": len(documents),
            "documents_total": data["documents_total"],
            "documents_processing_count": data["documents_processing_count"],
            "documents_page": data["documents_page"],
            "documents_page_size": data["documents_page_size"],
        },
    )


def table_body_partial_html(
    *,
    target_id: str,
    rows_html: str,
    data_attrs: dict[str, object] | None = None,
) -> str:
    return ui_partial_fragment_html(
        templates={target_id: rows_html},
        data_attrs=data_attrs or {},
    )


def _status_badge_html(status_value: str) -> str:
    status = str(status_value or "").lower()
    label = escape(_format_status(status))
    return f'<span class="status-badge status-{escape(status)}">{label}</span>'


def document_detail_fragments(initial_data: dict) -> dict:
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


def document_detail_partial_html(initial_data: dict) -> str:
    fragments = document_detail_fragments(initial_data)
    templates: list[str] = []
    for element_id, value in fragments.get("text", {}).items():
        templates.append(
            _partial_template(element_id, escape(str(value)), attr="data-text-target")
        )
    for element_id, value in fragments.get("html", {}).items():
        templates.append(
            _partial_template(element_id, str(value), attr="data-html-target")
        )
    for element_id, value in fragments.get("inputs", {}).items():
        templates.append(
            _partial_template(element_id, escape(str(value)), attr="data-input-target")
        )
    templates.append(
        _partial_template(
            "documentHistoryList",
            str(fragments.get("history_html") or ""),
            attr="data-html-target",
        )
    )
    data_attrs = {
        "document_id": fragments.get("document_id", ""),
        "document_label": fragments.get("document_label", ""),
        "blob_uri": fragments.get("blob_uri", ""),
    }
    return (
        f'<div class="ui-partial-fragment"{_fragment_data_attrs(data_attrs)}>'
        + "\n".join(templates)
        + "</div>"
    )


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


def chat_thread_list_html(
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
