from datetime import UTC, datetime, timedelta
from html import escape
import json
from urllib.parse import quote


_TAG_COLOR_SET = (
    "#8e5bcb",
    "#1d6a55",
    "#b0552f",
    "#c47a2a",
    "#2c6488",
    "#7a5c2e",
    "#8b4778",
    "#3d7a66",
    "#9f4a28",
    "#4f6f9f",
    "#6b5b95",
    "#2f7a8a",
)


def _stable_tag_color(value: str) -> str:
    normalized = str(value or "").strip().casefold()
    if not normalized:
        return "#7c8783"
    hash_value = 0
    for char in normalized:
        hash_value = ((hash_value * 33) + ord(char)) % 2147483647
    return _TAG_COLOR_SET[hash_value % len(_TAG_COLOR_SET)]


def _tag_color_style(value: str) -> str:
    return f' style="--tag-color: {_stable_tag_color(value)};"'


def _html_attr(value: object) -> str:
    return escape(str(value or ""), quote=True)


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
            f'<td data-label="Tag"><span class="tag-list-label"{_tag_color_style(raw_tag)}>'
            '<span class="tag-swatch" aria-hidden="true"></span>'
            f"<span>{tag}</span></span></td>"
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


def _format_document_size(value: int | None) -> str:
    bytes_value = int(value or 0)
    if bytes_value <= 0:
        return "-"
    if bytes_value < 1024 * 1024:
        kb = bytes_value / 1024
        return f"{kb:.1f} KB"
    mb = bytes_value / (1024 * 1024)
    return f"{mb:.1f} MB"


def _short_date(value: str | None) -> str:
    text = str(value or "").strip()
    if not text or text == "-":
        return "-"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.strftime("%b %-d, %Y")
    except ValueError:
        pass
    try:
        parsed = datetime.strptime(text[:10], "%Y-%m-%d")
        return parsed.strftime("%b %-d, %Y")
    except ValueError:
        return text


def _document_type_icon_class(content_type: str, filename: str) -> str:
    value = f"{content_type} {filename}".lower()
    if "pdf" in value:
        return "type-pdf"
    if "image" in value or value.endswith((".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff")):
        return "type-image"
    if "spreadsheet" in value or value.endswith((".csv", ".xls", ".xlsx")):
        return "type-spreadsheet"
    if "message" in value or value.endswith((".eml", ".msg")):
        return "type-email"
    return "type-file"


def _format_page_count(value: object) -> str:
    try:
        page_count = int(value or 0)
    except (TypeError, ValueError):
        page_count = 0
    if page_count <= 0:
        return ""
    return f"{page_count} page" if page_count == 1 else f"{page_count} pages"


def _initials(value: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned or cleaned == "-":
        return "-"
    parts = [part for part in cleaned.replace("-", " ").split() if part]
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    return cleaned[:2].upper()


def _sidebar_expand_button(*, group: str, hidden_count: int) -> str:
    group_attr = _html_attr(group)
    collapsed_label = f"Show all ({hidden_count} more)"
    return (
        f'<button type="button" class="docs-side-toggle" data-sidebar-toggle="{group_attr}" '
        f'data-collapsed-label="{_html_attr(collapsed_label)}" '
        'data-expanded-label="Show fewer" aria-expanded="false">'
        f"{escape(collapsed_label)}</button>"
    )


def document_sidebar_tags_html(tag_stats: list[dict], *, limit: int = 10) -> str:
    if not tag_stats:
        return '<span class="docs-side-empty">No tags yet</span>'
    rows: list[str] = []
    for stat in tag_stats:
        raw_tag = str(stat.get("tag") or "").strip()
        if not raw_tag:
            continue
        tag = escape(raw_tag)
        tag_query = quote(raw_tag, safe="")
        count = int(stat.get("document_count") or 0)
        hidden = ' hidden data-sidebar-extra="tags"' if len(rows) >= limit else ""
        rows.append(
            f'<a class="docs-side-row docs-tag-row" href="/ui/documents?tag={tag_query}"{hidden}>'
            f'<span class="tag-swatch"{_tag_color_style(raw_tag)} aria-hidden="true"></span>'
            f"<span>{tag}</span>"
            f'<span class="docs-side-count">{count:,}</span>'
            "</a>"
        )
    if not rows:
        return '<span class="docs-side-empty">No tags yet</span>'
    if len(rows) > limit:
        rows.append(_sidebar_expand_button(group="tags", hidden_count=len(rows) - limit))
    return "\n".join(rows)


def document_sidebar_document_types_html(type_stats: list[dict], *, limit: int = 10) -> str:
    if not type_stats:
        return '<span class="docs-side-empty">No document types yet</span>'
    rows: list[str] = []
    for stat in type_stats:
        raw_document_type = str(stat.get("document_type") or "").strip()
        if not raw_document_type:
            continue
        document_type = escape(raw_document_type)
        document_type_query = quote(raw_document_type, safe="")
        count = int(stat.get("document_count") or 0)
        hidden = ' hidden data-sidebar-extra="document-types"' if len(rows) >= limit else ""
        rows.append(
            f'<a class="docs-side-row docs-type-row" href="/ui/documents?document_type={document_type_query}"{hidden}>'
            '<span class="doc-type-dot" aria-hidden="true"></span>'
            f"<span>{document_type}</span>"
            f'<span class="docs-side-count">{count:,}</span>'
            "</a>"
        )
    if not rows:
        return '<span class="docs-side-empty">No document types yet</span>'
    if len(rows) > limit:
        rows.append(_sidebar_expand_button(group="document-types", hidden_count=len(rows) - limit))
    return "\n".join(rows)


def document_sidebar_correspondents_html(correspondent_stats: list[dict], *, limit: int = 10) -> str:
    if not correspondent_stats:
        return '<span class="docs-side-empty">No correspondents yet</span>'
    rows: list[str] = []
    for stat in correspondent_stats:
        raw_correspondent = str(stat.get("correspondent") or "").strip()
        if not raw_correspondent:
            continue
        correspondent = escape(raw_correspondent)
        correspondent_query = quote(raw_correspondent, safe="")
        count = int(stat.get("document_count") or 0)
        hidden = ' hidden data-sidebar-extra="correspondents"' if len(rows) >= limit else ""
        rows.append(
            f'<a class="docs-side-row docs-corr-row" href="/ui/documents?correspondent={correspondent_query}"{hidden}>'
            f'<span class="corr-avatar corr-avatar-sm" aria-hidden="true">{escape(_initials(raw_correspondent))}</span>'
            f"<span>{correspondent}</span>"
            f'<span class="docs-side-count">{count:,}</span>'
            "</a>"
        )
    if not rows:
        return '<span class="docs-side-empty">No correspondents yet</span>'
    if len(rows) > limit:
        rows.append(_sidebar_expand_button(group="correspondents", hidden_count=len(rows) - limit))
    return "\n".join(rows)


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
        return (
            '                <tr class="docs-empty-row"><td colspan="5">'
            '<div class="doc-empty"><div class="doc-empty-mark" aria-hidden="true">'
            '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M3 7h18"/><path d="M5 7l1 12h12l1-12"/><path d="M9 11h6"/>'
            "</svg></div><p>No documents are processing.</p></div></td></tr>"
        )
    rows: list[str] = []
    for item in documents:
        raw_document_id = str(item.get("id") or "")
        document_id = escape(raw_document_id)
        document_id_query = quote(raw_document_id, safe="")
        raw_title = _document_title(item)
        title = escape(raw_title)
        raw_filename = str(item.get("filename") or "Untitled document")
        filename = escape(raw_filename)
        status_html = _status_badge_html(str(item.get("status") or ""))
        stage = item.get("processing_stage") if isinstance(item.get("processing_stage"), dict) else {}
        stage_label = escape(str(stage.get("label") or "Processing"))
        stage_key = escape(str(stage.get("key") or "processing"), quote=True)
        try:
            stage_progress = max(0, min(100, int(stage.get("progress") or 0)))
        except (TypeError, ValueError):
            stage_progress = 0
        progress_html = (
            '<span class="pending-stage">'
            f'<span class="pending-stage-row"><span>{stage_label}</span><span>{stage_progress}%</span></span>'
            f'<span class="pending-stage-track" data-stage="{stage_key}">'
            f'<span style="width: {stage_progress}%"></span></span></span>'
        )
        created_at = escape(_short_date(str(item.get("created_at") or "-")))
        size = escape(_format_document_size(item.get("size_bytes")))
        content_type = escape(str(item.get("content_type") or "-"))
        type_icon_class = escape(
            _document_type_icon_class(str(item.get("content_type") or ""), str(item.get("filename") or "")),
            quote=True,
        )
        rows.append(
            f'                <tr class="doc-row pending-row" data-pending-doc-id="{document_id}">'
            '<td class="td td-title" data-label="Document">'
            f'<span class="type-icon {type_icon_class}" aria-hidden="true">'
            '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
            '<polyline points="14 2 14 8 20 8"/></svg></span>'
            '<span class="title-stack">'
            '<span class="title-row">'
            f'<a class="title-link" href="/ui/document?id={document_id_query}">{title}</a>'
            "</span>"
            f'<span class="title-meta"><span class="filename">{filename}</span></span>'
            "</span></td>"
            f'<td class="td td-status" data-label="Status">{status_html}{progress_html}</td>'
            f'<td class="td td-date-size" data-label="Queued"><span>{created_at}</span></td>'
            f'<td class="td td-file" data-label="File"><span>{size}</span><span class="td-meta">{content_type}</span></td>'
            '<td class="td td-actions" data-label="Action"><div class="table-actions">'
            f'<a class="row-act" href="/ui/document?id={document_id_query}" title="Open document" aria-label="Open document">'
            '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<polyline points="9 18 15 12 9 6"/></svg></a>'
            "</div></td>"
            "</tr>"
        )
    return "\n".join(rows)


def processing_strip_html(documents: list[dict], *, processing_count: int) -> str:
    normalized_count = max(0, int(processing_count or 0))
    if normalized_count <= 0:
        return ""
    items: list[dict[str, object]] = []
    for item in documents[:3]:
        if not isinstance(item, dict):
            continue
        stage = item.get("processing_stage") if isinstance(item.get("processing_stage"), dict) else {}
        filename = str(item.get("filename") or item.get("id") or "").strip()
        if not filename:
            continue
        try:
            progress = max(0, min(100, int(stage.get("progress") or 0)))
        except (TypeError, ValueError):
            progress = 0
        items.append(
            {
                "filename": filename,
                "stage_label": str(stage.get("label") or "Processing"),
                "stage_key": str(stage.get("key") or "processing"),
                "stage_progress": progress,
            }
        )
    if not items:
        items.append(
            {
                "filename": f"{normalized_count:,} document{'s' if normalized_count != 1 else ''}",
                "stage_label": "Processing",
                "stage_key": "processing",
                "stage_progress": 25,
            }
        )
    plural = "s" if normalized_count != 1 else ""
    files_html = "".join(f"<span>{escape(str(item['filename']))}</span>" for item in items)
    progress_rows = "".join(
        '<div class="inflight-progress-row">'
        f"<span>{escape(str(item['stage_label']))}</span>"
        f'<span class="inflight-progress-track" data-stage="{escape(str(item["stage_key"]), quote=True)}">'
        f'<span style="width: {int(item["stage_progress"])}%"></span></span>'
        "</div>"
        for item in items
    )
    return (
        '<div class="inflight-strip" data-processing-count="'
        f'{normalized_count}">'
        '<div class="inflight-copy">'
        '<div class="inflight-head">'
        '<span class="inflight-spin" aria-hidden="true"><span></span></span>'
        f'<a class="inflight-title" href="/ui/pending">{normalized_count:,} document{plural} processing</a>'
        "</div>"
        f'<div class="inflight-files">{files_html}</div>'
        "</div>"
        '<div class="inflight-progress" aria-label="Processing stages">'
        f"{progress_rows}"
        "</div>"
        '<a class="inflight-close" href="/ui/pending" aria-label="View processing queue">'
        '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></a>'
        "</div>"
    )


def document_rows_html(documents: list[dict]) -> str:
    if not documents:
        return (
            '                <tr class="docs-empty-row"><td colspan="6">'
            '<div class="doc-empty"><div class="doc-empty-mark" aria-hidden="true">'
            '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
            '<polyline points="14 2 14 8 20 8"/></svg></div>'
            "<p>No documents found.</p></div></td></tr>"
        )
    rows: list[str] = []
    for item in documents:
        raw_document_id = str(item.get("id") or "")
        document_id = escape(raw_document_id)
        document_id_query = quote(raw_document_id, safe="")
        raw_title = _document_title(item)
        title = escape(raw_title)
        raw_filename = str(item.get("filename") or "Untitled document")
        filename = escape(raw_filename)
        metadata = item.get("llm_metadata") if isinstance(item.get("llm_metadata"), dict) else {}
        document_type_raw = str(metadata.get("document_type") or "")
        document_type = str(document_type_raw or "-")
        correspondent_raw = str(metadata.get("correspondent") or "")
        correspondent = escape(correspondent_raw or "-")
        correspondent_query = quote(correspondent_raw, safe="")
        tags = metadata.get("tags") if isinstance(metadata.get("tags"), list) else []
        tag_pills = "".join(
            f'<a class="tag-pill" href="/ui/documents?tag={quote(str(tag), safe="")}"'
            f'{_tag_color_style(str(tag))}'
            f' data-full-tag="{_html_attr(str(tag))}">'
            '<span class="tag-swatch tag-swatch-xs" aria-hidden="true"></span>'
            f'<span class="tag-pill-label">{escape(str(tag))}</span></a>'
            for tag in tags[:3]
        )
        if len(tags) > 3:
            tag_pills += (
                f'<button type="button" class="tag-pill tag-more tag-more-button" '
                f'data-tags-expand="{document_id}" aria-label="Show all tags for {title}">'
                f"+{len(tags) - 3}</button>"
            )
        if not tag_pills:
            tag_pills = '<span class="muted">-</span>'
        document_date_raw = str(metadata.get("document_date") or "")
        display_date = escape(_short_date(document_date_raw))
        status_html = _document_list_status_badge_html(str(item.get("status") or ""))
        starred = bool(item.get("starred"))
        size = escape(_format_document_size(item.get("size_bytes")))
        page_count = escape(_format_page_count(item.get("page_count")))
        type_icon_class = escape(
            _document_type_icon_class(str(item.get("content_type") or ""), str(item.get("filename") or "")),
            quote=True,
        )
        title_meta_parts = [f'<span class="filename">{filename}</span>']
        if page_count:
            title_meta_parts.append(f'<span class="dot" aria-hidden="true"></span><span>{page_count}</span>')
        row_star = '<span class="row-star" aria-label="Starred document">★</span>' if starred else ""
        rows.append(
            f'                <tr class="doc-row" data-doc-id="{document_id}"'
            f' data-doc-title="{_html_attr(raw_title)}"'
            f' data-doc-filename="{_html_attr(raw_filename)}"'
            f' data-doc-date="{_html_attr(document_date_raw)}"'
            f' data-doc-correspondent="{_html_attr(correspondent_raw)}"'
            f' data-doc-type="{_html_attr(document_type_raw)}"'
            f' data-doc-starred="{"true" if starred else "false"}"'
            f' data-doc-tags="{_html_attr(json.dumps([str(tag) for tag in tags], ensure_ascii=True))}">'
            '<td class="td td-check" data-label="Select">'
            f'<input type="checkbox" data-doc-select="{document_id}" aria-label="Select {title}" /></td>'
            '<td class="td td-title" data-label="Document">'
            f'<span class="type-icon {type_icon_class}" aria-hidden="true">'
            '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
            '<polyline points="14 2 14 8 20 8"/></svg></span>'
            '<span class="title-stack">'
            '<span class="title-row">'
            f'<a class="title-link" href="/ui/document?id={document_id_query}">{title}</a>'
            f"{row_star}"
            f"{status_html}"
            "</span>"
            f'<span class="title-meta">{"".join(title_meta_parts)}</span>'
            "</span></td>"
            '<td class="td td-corr" data-label="Correspondent">'
            f'<span class="corr-cell"><span class="corr-avatar corr-avatar-sm">{escape(_initials(correspondent_raw))}</span>'
            f'<a class="corr-link" href="/ui/documents?correspondent={correspondent_query}">{correspondent}</a></span></td>'
            f'<td class="td td-tags" data-label="Tags">{tag_pills}</td>'
            f'<td class="td td-date-size" data-label="Date / Size"><span>{display_date}</span>'
            f'<span class="td-size-line">{size}</span></td>'
            '<td class="td td-actions" data-label="Action"><div class="table-actions">'
            f'<a class="row-act" href="/ui/document?id={document_id_query}" title="Open document" aria-label="Open document">'
            '<svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<polyline points="9 18 15 12 9 6"/></svg></a>'
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
    processing_label = (
        f'              <span id="docsProcessingLabel" class="docs-total-label">Processing: {normalized_processing_count:,}</span>\n'
        if normalized_processing_count > 0
        else ""
    )
    return (
        '            <div class="docs-summary">\n'
        f'              <span id="docsTotalLabel" class="docs-total-label">Total documents: {normalized_total:,}</span>\n'
        f"{processing_label}"
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
            "docsInflightRegion": processing_strip_html(
                data.get("pending_documents") if isinstance(data.get("pending_documents"), list) else [],
                processing_count=data["documents_processing_count"],
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


def _document_detail_tags_html(tags: list[object]) -> str:
    if not tags:
        return '<span class="tag-pill tag-empty">No tags</span>'
    return "".join(
        f'<a class="tag-pill" href="/ui/documents?tag={quote(str(tag), safe="")}"{_tag_color_style(str(tag))}>'
        '<span class="tag-swatch tag-swatch-xs" aria-hidden="true"></span>'
        f"{escape(str(tag))}</a>"
        for tag in tags
    )


def _short_date_label(value: object) -> str:
    raw_value = str(value or "")
    if not raw_value or raw_value == "-":
        return "-"
    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return raw_value[:10] if len(raw_value) >= 10 else raw_value
    return parsed.strftime("%b %d")


def _document_preview_kind(content_type: object, filename: object) -> str:
    value = f"{content_type or ''} {filename or ''}".strip().lower()
    if "image/" in value or value.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
        return "image"
    if "pdf" in value or value.endswith(".pdf"):
        return "pdf"
    return "embed"


def _normalize_detail_page_count(value: object) -> int:
    try:
        page_count = int(value or 0)
    except (TypeError, ValueError):
        page_count = 0
    return max(1, page_count)


def _document_page_thumbnails_html(page_count: int) -> str:
    normalized_count = _normalize_detail_page_count(page_count)
    lines = (
        '<span class="strip-line" style="width: 70%"></span>'
        '<span class="strip-line" style="width: 85%"></span>'
        '<span class="strip-line" style="width: 60%"></span>'
        '<span class="strip-line" style="width: 78%"></span>'
        '<span class="strip-line" style="width: 55%"></span>'
    )
    items = []
    for page_number in range(1, normalized_count + 1):
        active = " active" if page_number == 1 else ""
        current = ' aria-current="page"' if page_number == 1 else ""
        items.append(
            f'<button type="button" class="strip-thumb{active}" data-preview-page="{page_number}" '
            f'aria-label="Go to page {page_number}"{current}>'
            f'<span class="strip-thumb-page">{lines}</span>'
            f'<span class="strip-num">{page_number}</span>'
            "</button>"
        )
    return "\n".join(items)


def _initials(value: str) -> str:
    words = [word for word in str(value or "").replace("_", " ").split() if word]
    if not words:
        return "PW"
    if len(words) == 1:
        return words[0][:2].upper()
    return "".join(word[0] for word in words[:2]).upper()


def _document_list_status_badge_html(status_value: str) -> str:
    status = str(status_value or "").lower()
    if status == "ready":
        return ""
    return _status_badge_html(status)


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
    title = str(metadata.get("suggested_title") or document.get("filename") or document_id or "Untitled document")
    correspondent = str(metadata.get("correspondent") or "")
    document_date = str(metadata.get("document_date") or "")
    document_type = str(metadata.get("document_type") or "")
    content_type = str(document.get("content_type") or "-")
    filename = str(document.get("filename") or "-")
    preview_kind = _document_preview_kind(content_type, filename)
    page_count = _normalize_detail_page_count(document.get("page_count"))
    size_label = _format_bytes(size_bytes)
    ocr_preview = str(detail.get("ocr_text_preview") or "").strip()
    ocr_parsed_at = str(detail.get("ocr_parsed_at") or "-")
    file_meta = " · ".join(part for part in [content_type, size_label] if part and part != "-")
    file_url = f"/documents/{quote(document_id, safe='')}/file" if document_id else ""
    preview_url = file_url
    return {
        "document_id": document_id,
        "document_label": title,
        "blob_uri": str(document.get("blob_uri") or ""),
        "file_url": file_url,
        "preview_kind": preview_kind,
        "preview_url": preview_url,
        "text": {
            "detailTitle": title,
            "detailBreadcrumbTitle": title,
            "detailHeaderFileMeta": file_meta or "-",
            "detailCorrespondent": correspondent or "-",
            "detailDocumentDate": document_date or "-",
            "detailDocumentType": document_type or "-",
            "documentHistoryCount": f"{len(history)} event{'s' if len(history) != 1 else ''}",
            "documentHistoryTabCount": str(len(history)),
            "detailOcrCharCount": f"{len(ocr_preview):,} chars",
            "detailOcrParsedShort": _short_date_label(ocr_parsed_at),
            "detailDocId": document_id or "-",
            "detailOwnerId": str(document.get("owner_id") or "-"),
            "detailFilename": filename,
            "detailCreatedAt": str(document.get("created_at") or "-"),
            "detailOcrParsedAt": ocr_parsed_at,
            "detailContentType": content_type,
            "detailSizeBytes": f"{_format_bytes(size_bytes)} ({size_bytes} bytes)",
            "detailChecksum": str(document.get("checksum_sha256") or "-"),
            "detailBlobUri": _relative_blob_path(str(document.get("blob_uri") or "")),
            "detailOcrContent": ocr_preview or "-",
            "previewCurrentPage": "1",
            "previewTotalPages": str(page_count),
        },
        "html": {
            "detailStatus": _status_badge_html(str(document.get("status") or "")),
            "detailTagPills": _document_detail_tags_html(tags),
            "pageStrip": _document_page_thumbnails_html(page_count),
        },
        "inputs": {
            "metaTitle": title,
            "metaDate": document_date,
            "metaCorrespondent": correspondent,
            "metaType": document_type,
            "metaTags": ", ".join(str(tag) for tag in tags),
        },
        "tags_html": _document_detail_tags_html(tags),
        "file_meta": file_meta or "-",
        "history_count": f"{len(history)} event{'s' if len(history) != 1 else ''}",
        "history_count_short": str(len(history)),
        "ocr_char_count": f"{len(ocr_preview):,}",
        "ocr_parsed_short": _short_date_label(ocr_parsed_at),
        "page_count": page_count,
        "page_thumbnails_html": _document_page_thumbnails_html(page_count),
        "preview_kind": preview_kind,
        "correspondent_initials": _initials(correspondent or title),
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
        "file_url": fragments.get("file_url", ""),
        "preview_kind": fragments.get("preview_kind", ""),
        "preview_url": fragments.get("preview_url", ""),
        "page_count": str(fragments.get("page_count", 1)),
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
