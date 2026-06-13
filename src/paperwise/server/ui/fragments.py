from datetime import UTC, datetime, timedelta
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from paperwise.server.ui.tag_colors import stable_tag_color

_SERVER_DIR = Path(__file__).resolve().parent.parent
_FRAGMENT_TEMPLATE_ENV = Environment(
    loader=FileSystemLoader(_SERVER_DIR / "templates" / "ui" / "fragments"),
    autoescape=select_autoescape(("html", "xml")),
    trim_blocks=True,
    lstrip_blocks=True,
)
_FRAGMENT_TEMPLATE_ENV.filters["format_number"] = lambda value: f"{int(value or 0):,}"


def _render_fragment_template(template_name: str, **context: object) -> str:
    return _FRAGMENT_TEMPLATE_ENV.get_template(template_name).render(context).strip()


def _stable_tag_color(value: str) -> str:
    return stable_tag_color(value)


def tag_rows_html(tag_stats: list[dict]) -> str:
    rows = [
        {
            "tag": str(stat.get("tag") or ""),
            "tag_query": quote(str(stat.get("tag") or ""), safe=""),
            "count": int(stat.get("document_count") or 0),
            "color": _stable_tag_color(str(stat.get("tag") or "")),
        }
        for stat in tag_stats
    ]
    return _render_fragment_template("tag_rows.html", rows=rows)


def document_type_rows_html(type_stats: list[dict]) -> str:
    rows = [
        {
            "document_type": str(stat.get("document_type") or ""),
            "document_type_query": quote(str(stat.get("document_type") or ""), safe=""),
            "count": int(stat.get("document_count") or 0),
        }
        for stat in type_stats
    ]
    return _render_fragment_template("document_type_rows.html", rows=rows)


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


def _status_badge_context(status_value: str, *, hide_ready: bool = False) -> dict[str, str] | None:
    status = str(status_value or "").lower()
    if hide_ready and status == "ready":
        return None
    return {"status": status, "label": _format_status(status)}


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
    parts = [part for part in cleaned.replace("-", " ").replace("_", " ").split() if part]
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    return cleaned[:2].upper()


def document_sidebar_tags_html(tag_stats: list[dict], *, limit: int = 10) -> str:
    rows = []
    for stat in tag_stats:
        raw_tag = str(stat.get("tag") or "").strip()
        if not raw_tag:
            continue
        rows.append(
            {
                "label": raw_tag,
                "href": f"/ui/documents?tag={quote(raw_tag, safe='')}",
                "count": int(stat.get("document_count") or 0),
                "hidden": len(rows) >= limit,
                "color": _stable_tag_color(raw_tag),
            }
        )
    return _render_fragment_template(
        "document_sidebar_rows.html",
        rows=rows,
        empty_label="No tags yet",
        row_class="docs-tag-row",
        group="tags",
        hidden_count=max(0, len(rows) - limit),
        kind="tags",
    )


def document_sidebar_document_types_html(type_stats: list[dict], *, limit: int = 10) -> str:
    rows = []
    for stat in type_stats:
        raw_document_type = str(stat.get("document_type") or "").strip()
        if not raw_document_type:
            continue
        rows.append(
            {
                "label": raw_document_type,
                "href": f"/ui/documents?document_type={quote(raw_document_type, safe='')}",
                "count": int(stat.get("document_count") or 0),
                "hidden": len(rows) >= limit,
            }
        )
    return _render_fragment_template(
        "document_sidebar_rows.html",
        rows=rows,
        empty_label="No document types yet",
        row_class="docs-type-row",
        group="document-types",
        hidden_count=max(0, len(rows) - limit),
        kind="document-types",
    )


def document_sidebar_correspondents_html(correspondent_stats: list[dict], *, limit: int = 10) -> str:
    rows = []
    for stat in correspondent_stats:
        raw_correspondent = str(stat.get("correspondent") or "").strip()
        if not raw_correspondent:
            continue
        rows.append(
            {
                "label": raw_correspondent,
                "href": f"/ui/documents?correspondent={quote(raw_correspondent, safe='')}",
                "count": int(stat.get("document_count") or 0),
                "hidden": len(rows) >= limit,
                "initials": _initials(raw_correspondent),
            }
        )
    return _render_fragment_template(
        "document_sidebar_rows.html",
        rows=rows,
        empty_label="No correspondents yet",
        row_class="docs-corr-row",
        group="correspondents",
        hidden_count=max(0, len(rows) - limit),
        kind="correspondents",
    )


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
    items = []
    for event in events:
        items.append(
            {
                "event_type": _format_history_event_type(str(event.get("event_type") or "")),
                "actor": _format_history_actor(event),
                "source": str(event.get("source") or "-"),
                "created_at": str(event.get("created_at") or "-"),
                "changes": _history_change_lines(event),
            }
        )
    return _render_fragment_template("document_history.html", items=items)


def _document_chat_threads_html(threads: list[dict]) -> str:
    items = []
    for thread in threads:
        raw_thread_id = str(thread.get("id") or "")
        updated = _chat_thread_time_label(str(thread.get("updated_at") or thread.get("created_at") or ""))
        message_count = int(thread.get("message_count") or 0)
        reference_count = int(thread.get("reference_count") or 0)
        message_label = f"{message_count} msg" if message_count == 1 else f"{message_count} msgs"
        reference_label = f"{reference_count} ref" if reference_count == 1 else f"{reference_count} refs"
        sources = thread.get("source_titles") if isinstance(thread.get("source_titles"), list) else []
        items.append(
            {
                "thread_query": quote(raw_thread_id, safe=""),
                "title": str(thread.get("title") or "Untitled chat"),
                "question": str(thread.get("question") or "").strip(),
                "meta": " | ".join(item for item in (updated, message_label, reference_label) if item),
                "sources": [str(source) for source in sources],
            }
        )
    return _render_fragment_template("document_chat_threads.html", items=items)


def activity_rows_html(documents: list[dict]) -> str:
    rows = []
    for item in documents:
        raw_document_id = str(item.get("id") or "")
        rows.append(
            {
                "document_id_query": quote(raw_document_id, safe=""),
                "title": _document_title(item),
                "status": _status_badge_context(str(item.get("status") or "")),
                "created_at": str(item.get("created_at") or "-"),
            }
        )
    return _render_fragment_template("activity_rows.html", rows=rows)


def pending_rows_html(documents: list[dict]) -> str:
    rows = []
    for item in documents:
        raw_document_id = str(item.get("id") or "")
        raw_filename = str(item.get("filename") or "Untitled document")
        stage = item.get("processing_stage") if isinstance(item.get("processing_stage"), dict) else {}
        try:
            stage_progress = max(0, min(100, int(stage.get("progress") or 0)))
        except (TypeError, ValueError):
            stage_progress = 0
        rows.append(
            {
                "document_id": raw_document_id,
                "document_id_query": quote(raw_document_id, safe=""),
                "title": _document_title(item),
                "filename": raw_filename,
                "status": _status_badge_context(str(item.get("status") or "")),
                "stage_label": str(stage.get("label") or "Processing"),
                "stage_key": str(stage.get("key") or "processing"),
                "stage_progress": stage_progress,
                "created_at": _short_date(str(item.get("created_at") or "-")),
                "size": _format_document_size(item.get("size_bytes")),
                "content_type": str(item.get("content_type") or "-"),
                "type_icon_class": _document_type_icon_class(
                    str(item.get("content_type") or ""),
                    str(item.get("filename") or ""),
                ),
            }
        )
    return _render_fragment_template("pending_rows.html", rows=rows)


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
    return _render_fragment_template(
        "processing_strip.html",
        processing_count=normalized_count,
        plural="s" if normalized_count != 1 else "",
        items=items,
    )


def _document_processing_stage_html(document: dict) -> str:
    status = str(document.get("status") or "").strip().lower()
    if status not in {"received", "processing"}:
        return ""
    stage = document.get("processing_stage") if isinstance(document.get("processing_stage"), dict) else {}
    try:
        progress = max(0, min(100, int(stage.get("progress") or 0)))
    except (TypeError, ValueError):
        progress = 0
    return _render_fragment_template(
        "document_processing_stage.html",
        stage_label=str(stage.get("label") or "Processing"),
        stage_key=str(stage.get("key") or "processing"),
        stage_progress=progress,
    )


def document_rows_html(documents: list[dict]) -> str:
    rows = []
    for item in documents:
        raw_document_id = str(item.get("id") or "")
        raw_title = _document_title(item)
        raw_filename = str(item.get("filename") or "Untitled document")
        metadata = item.get("llm_metadata") if isinstance(item.get("llm_metadata"), dict) else {}
        document_type_raw = str(metadata.get("document_type") or "")
        document_type = str(document_type_raw or "-")
        correspondent_raw = str(metadata.get("correspondent") or "")
        tags = metadata.get("tags") if isinstance(metadata.get("tags"), list) else []
        document_date_raw = str(metadata.get("document_date") or "")
        starred = bool(item.get("starred"))
        tag_rows = [
            {
                "label": str(tag),
                "href": f"/ui/documents?tag={quote(str(tag), safe='')}",
                "color": _stable_tag_color(str(tag)),
            }
            for tag in tags[:3]
        ]
        rows.append(
            {
                "document_id": raw_document_id,
                "document_id_query": quote(raw_document_id, safe=""),
                "raw_title": raw_title,
                "raw_filename": raw_filename,
                "document_date_raw": document_date_raw,
                "correspondent_raw": correspondent_raw,
                "document_type_raw": document_type_raw,
                "document_type": document_type,
                "starred": starred,
                "tags_json_attr": escape(json.dumps([str(tag) for tag in tags], ensure_ascii=True), quote=True),
                "title": raw_title,
                "filename": raw_filename,
                "status": _status_badge_context(str(item.get("status") or ""), hide_ready=True),
                "correspondent": correspondent_raw or "-",
                "correspondent_query": quote(correspondent_raw, safe=""),
                "correspondent_initials": _initials(correspondent_raw),
                "tags": tag_rows,
                "hidden_tag_count": max(0, len(tags) - 3),
                "display_date": _short_date(document_date_raw),
                "size": _format_document_size(item.get("size_bytes")),
                "page_count": _format_page_count(item.get("page_count")),
                "type_icon_class": _document_type_icon_class(
                    str(item.get("content_type") or ""),
                    str(item.get("filename") or ""),
                ),
            }
        )
    return _render_fragment_template("document_rows.html", rows=rows)


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
    range_start = ((normalized_page - 1) * normalized_page_size + 1) if normalized_total > 0 else 0
    range_end = min(normalized_total, normalized_page * normalized_page_size)
    page_digits = max(2, len(str(total_pages)))
    display_page = f"{normalized_page:0{page_digits}d}"
    display_total_pages = f"{total_pages:0{page_digits}d}"
    return _render_fragment_template(
        "documents_pagination_toolbar.html",
        range_start=range_start,
        range_end=range_end,
        total=normalized_total,
        processing_count=normalized_processing_count,
        display_page=display_page,
        display_total_pages=display_total_pages,
        first_prev_disabled=normalized_page <= 1,
        next_last_disabled=normalized_page >= total_pages,
    )


def ui_partial_fragment_html(
    *,
    templates: dict[str, str],
    data_attrs: dict[str, object] | None = None,
) -> str:
    template_rows = [
        {"target_id": target_id, "html": html, "attr": "data-partial-target"}
        for target_id, html in templates.items()
    ]
    return _render_fragment_template(
        "ui_partial_fragment.html",
        data_attrs=data_attrs or {},
        templates=template_rows,
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
    return _render_fragment_template("status_badge.html", badge=_status_badge_context(status_value))


def _document_detail_tags_html(tags: list[object]) -> str:
    tag_rows = [
        {
            "label": str(tag),
            "href": f"/ui/documents?tag={quote(str(tag), safe='')}",
            "color": _stable_tag_color(str(tag)),
        }
        for tag in tags
    ]
    return _render_fragment_template("document_detail_tags.html", tags=tag_rows)


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
    if "image/" in value or value.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".tif", ".tiff")):
        return "image"
    if "pdf" in value or value.endswith(".pdf"):
        return "pdf"
    if "text/markdown" in value or value.endswith((".markdown", ".md")):
        return "markdown"
    if (
        "text/plain" in value
        or "application/msword" in value
        or "application/rtf" in value
        or "application/vnd.ms-excel" in value
        or "application/vnd.ms-powerpoint" in value
        or "application/vnd.oasis.opendocument" in value
        or "application/vnd.openxmlformats-officedocument.presentationml.presentation" in value
        or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in value
        or "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in value
        or "text/csv" in value
        or "text/rtf" in value
        or "text/tab-separated-values" in value
        or value.endswith((".csv", ".doc", ".docx", ".odp", ".ods", ".odt", ".ppt", ".pptx", ".rtf", ".tsv", ".txt", ".xls", ".xlsx"))
    ):
        return "text"
    return "embed"


def _normalize_detail_page_count(value: object) -> int:
    try:
        page_count = int(value or 0)
    except (TypeError, ValueError):
        page_count = 0
    return max(1, page_count)


def _document_preview_page_count(*, preview_kind: str, page_count: object) -> int:
    if preview_kind in {"markdown", "text"}:
        return 1
    return _normalize_detail_page_count(page_count)


def _render_markdown_inline(text: str) -> str:
    rendered = escape(str(text or ""))
    rendered = re.sub(r"`([^`]+)`", r"<code>\1</code>", rendered)
    rendered = re.sub(
        r"\[([^\]]+)\]\(((?:https?://|mailto:)[^\s)]+)\)",
        r'<a href="\2" rel="noopener noreferrer" target="_blank">\1</a>',
        rendered,
    )
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"(^|[\s(])\*([^*]+)\*(?=$|[\s).,!?;:])", r"\1<em>\2</em>", rendered)
    return rendered


def _flush_markdown_paragraph(buffer: list[str], html: list[str]) -> None:
    if not buffer:
        return
    html.append(f"<p>{'<br>'.join(_render_markdown_inline(line) for line in buffer)}</p>")
    buffer.clear()


def _render_markdown_preview(markdown: str) -> str:
    lines = str(markdown or "").replace("\r\n", "\n").split("\n")
    html: list[str] = []
    paragraph: list[str] = []
    list_kind = ""
    in_code = False
    code_lines: list[str] = []

    def close_list() -> None:
        nonlocal list_kind
        if list_kind:
            html.append(f"</{list_kind}>")
            list_kind = ""

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                html.append(f"<pre><code>{escape(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
                in_code = False
            else:
                close_list()
                _flush_markdown_paragraph(paragraph, html)
                in_code = True
                code_lines = []
            continue

        if in_code:
            code_lines.append(raw_line.rstrip("\n"))
            continue

        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        quote_match = re.match(r"^>\s+(.+)$", line)
        unordered = re.match(r"^[-*]\s+(.+)$", line)
        ordered = re.match(r"^(\d+)\.\s+(.+)$", line)

        if not stripped:
            _flush_markdown_paragraph(paragraph, html)
            close_list()
            continue

        if heading:
            close_list()
            _flush_markdown_paragraph(paragraph, html)
            level = len(heading.group(1))
            html.append(f"<h{level}>{_render_markdown_inline(heading.group(2))}</h{level}>")
            continue

        if quote_match:
            close_list()
            _flush_markdown_paragraph(paragraph, html)
            html.append(f"<blockquote>{_render_markdown_inline(quote_match.group(1))}</blockquote>")
            continue

        if unordered:
            _flush_markdown_paragraph(paragraph, html)
            if list_kind != "ul":
                close_list()
                html.append("<ul>")
                list_kind = "ul"
            html.append(f"<li>{_render_markdown_inline(unordered.group(1))}</li>")
            continue

        if ordered:
            _flush_markdown_paragraph(paragraph, html)
            if list_kind != "ol":
                close_list()
                start = int(ordered.group(1) or "1")
                html.append(f'<ol start="{start}">' if start > 1 else "<ol>")
                list_kind = "ol"
            html.append(f"<li>{_render_markdown_inline(ordered.group(2))}</li>")
            continue

        close_list()
        paragraph.append(line)

    if in_code:
        html.append(f"<pre><code>{escape(chr(10).join(code_lines))}</code></pre>")
    close_list()
    _flush_markdown_paragraph(paragraph, html)
    return "".join(html) or "<p>Extracted text will appear after processing completes.</p>"


def _document_page_thumbnails_html(page_count: int) -> str:
    normalized_count = _normalize_detail_page_count(page_count)
    return _render_fragment_template(
        "document_page_thumbnails.html",
        page_numbers=list(range(1, normalized_count + 1)),
        line_widths=(70, 85, 60, 78, 55),
    )


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
    chat_threads = (
        initial_data.get("document_chat_threads")
        if isinstance(initial_data.get("document_chat_threads"), list)
        else []
    )
    title = str(metadata.get("suggested_title") or document.get("filename") or document_id or "Untitled document")
    correspondent = str(metadata.get("correspondent") or "")
    document_date = str(metadata.get("document_date") or "")
    document_type = str(metadata.get("document_type") or "")
    content_type = str(document.get("content_type") or "-")
    filename = str(document.get("filename") or "-")
    preview_kind = _document_preview_kind(content_type, filename)
    page_count = _document_preview_page_count(
        preview_kind=preview_kind,
        page_count=document.get("page_count"),
    )
    size_label = _format_bytes(size_bytes)
    ocr_preview = str(detail.get("ocr_text_preview") or "").strip()
    ocr_parsed_at = str(detail.get("ocr_parsed_at") or "-")
    file_meta = " · ".join(part for part in [content_type, size_label] if part and part != "-")
    file_url = f"/documents/{quote(document_id, safe='')}/file" if document_id else ""
    preview_url = "" if preview_kind in {"markdown", "text"} else file_url
    text_preview = ocr_preview or "Extracted text will appear after processing completes."
    markdown_preview_html = _render_markdown_preview(ocr_preview) if preview_kind == "markdown" else ""
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
            "documentThreadsTabCount": str(len(chat_threads)),
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
            "detailTextPreview": text_preview,
            "previewCurrentPage": "1",
            "previewTotalPages": str(page_count),
        },
        "html": {
            "detailStatus": _status_badge_html(str(document.get("status") or "")),
            "detailProcessingStage": _document_processing_stage_html(document),
            "detailTagPills": _document_detail_tags_html(tags),
            "detailMarkdownPreview": markdown_preview_html,
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
        "chat_thread_count": f"{len(chat_threads)} thread{'s' if len(chat_threads) != 1 else ''}",
        "chat_thread_count_short": str(len(chat_threads)),
        "chat_threads_html": _document_chat_threads_html(chat_threads),
        "ocr_char_count": f"{len(ocr_preview):,}",
        "ocr_parsed_short": _short_date_label(ocr_parsed_at),
        "page_count": page_count,
        "page_thumbnails_html": _document_page_thumbnails_html(page_count),
        "preview_kind": preview_kind,
        "preview_url": preview_url,
        "status": str(document.get("status") or ""),
        "correspondent_initials": _initials(correspondent or title),
        "history_html": _history_html(history),
    }


def document_detail_partial_html(initial_data: dict) -> str:
    fragments = document_detail_fragments(initial_data)
    templates: list[dict[str, str]] = []
    for element_id, value in fragments.get("text", {}).items():
        templates.append(
            {"target_id": element_id, "html": escape(str(value)), "attr": "data-text-target"}
        )
    for element_id, value in fragments.get("html", {}).items():
        templates.append(
            {"target_id": element_id, "html": str(value), "attr": "data-html-target"}
        )
    for element_id, value in fragments.get("inputs", {}).items():
        templates.append(
            {"target_id": element_id, "html": escape(str(value)), "attr": "data-input-target"}
        )
    templates.append(
        {
            "target_id": "documentHistoryList",
            "html": str(fragments.get("history_html") or ""),
            "attr": "data-html-target",
        }
    )
    templates.append(
        {
            "target_id": "documentThreadList",
            "html": str(fragments.get("chat_threads_html") or ""),
            "attr": "data-html-target",
        }
    )
    data_attrs = {
        "document_id": fragments.get("document_id", ""),
        "document_label": fragments.get("document_label", ""),
        "blob_uri": fragments.get("blob_uri", ""),
        "file_url": fragments.get("file_url", ""),
        "preview_kind": fragments.get("preview_kind", ""),
        "preview_url": fragments.get("preview_url", ""),
        "page_count": str(fragments.get("page_count", 1)),
        "document_status": fragments.get("status", ""),
    }
    return _render_fragment_template(
        "ui_partial_fragment.html",
        data_attrs=data_attrs,
        templates=templates,
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
        return _render_fragment_template("chat_thread_list.html", empty_message=message, sections=[])

    sections = []
    for bucket, label in (("today", "Today"), ("yesterday", "Yesterday"), ("earlier", "Earlier")):
        items = [thread for thread in filtered_threads if _chat_thread_bucket(thread) == bucket]
        if not items:
            continue
        rows = []
        for thread in items:
            raw_thread_id = str(thread.get("id") or "")
            title = str(thread.get("title") or "Untitled chat")
            updated = _chat_thread_time_label(str(thread.get("updated_at") or thread.get("created_at") or ""))
            count = int(thread.get("message_count") or 0)
            count_label = f"{count} msg" if count == 1 else f"{count} msgs"
            rows.append(
                {
                    "thread_id": raw_thread_id,
                    "title": title,
                    "meta": " | ".join(item for item in (updated, count_label) if item),
                    "active": raw_thread_id == active_thread_id,
                }
            )
        sections.append(
            {
                "label": label,
                "rows": rows,
            }
        )
    return _render_fragment_template("chat_thread_list.html", empty_message="", sections=sections)
