from pathlib import Path
import json
import re

from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from paperwise.server.ui.fragments import (
    activity_rows_html,
    chat_thread_list_html,
    document_detail_fragments,
    document_rows_html,
    document_sidebar_correspondents_html,
    document_sidebar_document_types_html,
    document_sidebar_tags_html,
    document_type_rows_html,
    documents_pagination_toolbar_html,
    pending_rows_html,
    tag_rows_html,
)

_SERVER_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = _SERVER_DIR / "static"
_STATIC_CSS_DIR = STATIC_DIR / "css"
_STATIC_JS_DIR = STATIC_DIR / "js"
_TEMPLATE_DIR = _SERVER_DIR / "templates" / "ui"
_TEMPLATE_ENV = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(("html", "xml")),
)
_TEMPLATE_ENV.filters["format_number"] = lambda value: f"{int(value or 0):,}"
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
    "documents": "partials/documents.html",
    "document": "partials/document.html",
    "search": "partials/search.html",
    "grounded-qa": "partials/grounded_qa.html",
    "tags": "partials/tags.html",
    "document-types": "partials/document_types.html",
    "pending": "partials/pending.html",
    "upload": "partials/upload.html",
    "activity": "partials/activity.html",
    "settings-display": "partials/settings_display.html",
    "settings-account": "partials/settings_account.html",
    "settings-models": "partials/settings_models.html",
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


def render_ui_page(
    view_id: str,
    *,
    page_name: str,
    initial_data: dict | None = None,
    active_nav_href: str | None = None,
) -> HTMLResponse:
    script_names = ["shared.js", "app.js", *_PAGE_SCRIPTS_BY_VIEW.get(view_id, [])]
    asset_version = str(
        max(
            *[path.stat().st_mtime_ns for path in _STATIC_CSS_DIR.glob("*.css")],
            *[(_STATIC_JS_DIR / script_name).stat().st_mtime_ns for script_name in script_names],
        )
    )
    asset_query = f"?v={asset_version}"
    initial_data_json = ""
    if initial_data is not None:
        initial_data_json = json.dumps(initial_data, ensure_ascii=True).replace("</", "<\\/")
    context = {
        **_initial_render_context(initial_data or {}),
        "active_nav_href": active_nav_href or _ACTIVE_NAV_BY_VIEW.get(view_id, "/ui/documents"),
        "asset_query": asset_query,
        "authenticated": bool(initial_data and initial_data.get("authenticated") is True),
        "default_ui_theme": DEFAULT_UI_THEME,
        "grounded_qa_model_label": _grounded_qa_model_label(initial_data or {}),
        "initial_data_json": initial_data_json,
        "page_module_name": script_names[2] if len(script_names) > 2 else "",
        "page_template": _PAGE_PARTIAL_BY_NAME[page_name],
        "settings_preferences": _settings_preferences_context(initial_data or {}),
        "supported_ui_themes": list(SUPPORTED_UI_THEMES),
        "ui_theme_storage_key": UI_THEME_STORAGE_KEY,
    }
    html = _TEMPLATE_ENV.get_template("layout.html").render(context)

    return HTMLResponse(
        html,
        headers={"Cache-Control": "no-store"},
    )


def _processing_filenames(documents: object, *, limit: int = 3) -> list[str]:
    if not isinstance(documents, list):
        return []
    filenames: list[str] = []
    for item in documents[:limit]:
        if not isinstance(item, dict):
            continue
        filename = str(item.get("filename") or item.get("id") or "").strip()
        if filename:
            filenames.append(filename)
    return filenames


def _processing_items(documents: object, *, limit: int = 3) -> list[dict[str, object]]:
    if not isinstance(documents, list):
        return []
    items: list[dict[str, object]] = []
    for item in documents[:limit]:
        if not isinstance(item, dict):
            continue
        stage = item.get("processing_stage") if isinstance(item.get("processing_stage"), dict) else {}
        filename = str(item.get("filename") or item.get("id") or "").strip()
        if not filename:
            continue
        items.append(
            {
                "filename": filename,
                "stage_label": str(stage.get("label") or "Processing"),
                "stage_key": str(stage.get("key") or "processing"),
                "stage_progress": max(0, min(100, int(stage.get("progress") or 0))),
            }
        )
    return items


def _grounded_qa_model_label(initial_data: dict) -> str:
    preferences = initial_data.get("user_preferences")
    if not isinstance(preferences, dict):
        return "Default model"
    routing = preferences.get("llm_routing")
    connections = preferences.get("llm_connections")
    if not isinstance(routing, dict) or not isinstance(connections, list):
        return "Default model"
    grounded_route = routing.get("grounded_qa")
    if not isinstance(grounded_route, dict):
        return "Default model"
    connection_id = str(grounded_route.get("connection_id") or "").strip()
    connection = next(
        (
            item
            for item in connections
            if isinstance(item, dict) and str(item.get("id") or "").strip() == connection_id
        ),
        None,
    )
    if not connection:
        return "Default model"
    provider = str(connection.get("provider") or "").strip()
    route_model = str(grounded_route.get("model") or "").strip()
    connection_model = str(connection.get("default_model") or "").strip()
    defaults = initial_data.get("llm_provider_defaults")
    default_model = ""
    if isinstance(defaults, dict) and provider in defaults and isinstance(defaults[provider], dict):
        default_model = str(defaults[provider].get("model") or "").strip()
    parts = [part for part in (provider, route_model or connection_model or default_model) if part]
    return " · ".join(parts) if parts else "Default model"


def _settings_preferences_context(initial_data: dict) -> dict:
    preferences = initial_data.get("user_preferences")
    if not isinstance(preferences, dict):
        preferences = {}
    ui_theme = str(preferences.get("ui_theme") or DEFAULT_UI_THEME).strip().lower()
    if ui_theme not in SUPPORTED_UI_THEMES:
        ui_theme = DEFAULT_UI_THEME

    def bounded_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
        try:
            number = int(value or default)
        except (TypeError, ValueError):
            number = default
        return max(minimum, min(maximum, number))

    page_size = bounded_int(preferences.get("page_size"), default=20, minimum=1, maximum=100)
    if page_size not in {10, 20, 50, 100}:
        page_size = 20
    top_k = bounded_int(preferences.get("grounded_qa_top_k_chunks"), default=18, minimum=2, maximum=48)
    max_documents = bounded_int(preferences.get("grounded_qa_max_documents"), default=12, minimum=1, maximum=24)
    return {
        "ui_theme": ui_theme,
        "page_size": page_size,
        "grounded_qa_top_k_chunks": top_k,
        "grounded_qa_max_documents": max_documents,
    }


def _initial_render_context(initial_data: dict) -> dict:
    documents = initial_data.get("documents")
    tags = initial_data.get("tag_stats")
    sidebar_tags = initial_data.get("document_sidebar_tags")
    sidebar_document_types = initial_data.get("document_sidebar_document_types")
    sidebar_correspondents = initial_data.get("document_sidebar_correspondents")
    document_types = initial_data.get("document_type_stats")
    activity_documents = initial_data.get("activity_documents")
    pending_documents = initial_data.get("pending_documents")
    chat_threads = initial_data.get("chat_threads")
    fragments = document_detail_fragments(initial_data)
    total = int(initial_data.get("documents_total") or 0)
    processing_count = int(initial_data.get("documents_processing_count") or 0)
    page = max(1, int(initial_data.get("documents_page") or 1))
    page_size = max(1, int(initial_data.get("documents_page_size") or 20))
    return {
        "activity_table_body_html": activity_rows_html(
            activity_documents if isinstance(activity_documents, list) else []
        ),
        "activity_total_tokens": int(initial_data.get("activity_total_tokens") or 0),
        "chat_thread_list_html": chat_thread_list_html(
            chat_threads if isinstance(chat_threads, list) else []
        ),
        "document_detail_blob_uri": fragments["blob_uri"],
        "document_detail_correspondent_initials": fragments.get("correspondent_initials", "PW"),
        "document_detail_file_meta": fragments.get("file_meta", "-"),
        "document_detail_file_url": fragments.get("file_url", ""),
        "document_detail_preview_url": fragments.get("preview_url", ""),
        "document_detail_page_count": fragments.get("page_count", 1),
        "document_detail_starred": bool((initial_data.get("document_detail") or {}).get("document", {}).get("starred")),
        "document_detail_page_thumbnails_html": fragments.get("page_thumbnails_html", ""),
        "document_detail_inputs": fragments["inputs"],
        "document_detail_status_html": fragments["html"].get("detailStatus", "-"),
        "document_detail_tags_html": fragments.get("tags_html", ""),
        "document_detail_text": fragments["text"],
        "document_detail_title": fragments["text"].get("detailTitle", "Untitled document"),
        "document_history_count": fragments.get("history_count", "0 events"),
        "document_history_count_short": fragments.get("history_count_short", "0"),
        "document_detail_ocr_char_count": fragments.get("ocr_char_count", "0"),
        "document_detail_ocr_parsed_short": fragments.get("ocr_parsed_short", "-"),
        "document_history_html": fragments["history_html"],
        "document_types_table_body_html": document_type_rows_html(
            document_types if isinstance(document_types, list) else []
        ),
        "documents_pagination_toolbar_html": documents_pagination_toolbar_html(
            total=total,
            processing_count=processing_count,
            page=page,
            page_size=page_size,
        ),
        "documents_total": total,
        "documents_processing_count": processing_count,
        "documents_all_count": int(initial_data.get("documents_all_count") or total),
        "documents_failed_count": int(initial_data.get("documents_failed_count") or 0),
        "documents_failed_filter": bool(initial_data.get("documents_failed_filter")),
        "documents_processing_filenames": _processing_filenames(pending_documents),
        "documents_processing_items": _processing_items(pending_documents),
        "documents_starred_count": int(initial_data.get("documents_starred_count") or 0),
        "documents_starred_filter": bool(initial_data.get("documents_starred_filter")),
        "documents_sidebar_correspondents_html": document_sidebar_correspondents_html(
            sidebar_correspondents if isinstance(sidebar_correspondents, list) else []
        ),
        "documents_sidebar_document_types_html": document_sidebar_document_types_html(
            sidebar_document_types if isinstance(sidebar_document_types, list) else []
        ),
        "documents_sidebar_tags_html": document_sidebar_tags_html(
            sidebar_tags if isinstance(sidebar_tags, list) else []
        ),
        "documents_table_body_html": document_rows_html(
            documents if isinstance(documents, list) else []
        ),
        "pending_table_body_html": pending_rows_html(
            pending_documents if isinstance(pending_documents, list) else []
        ),
        "tags_table_body_html": tag_rows_html(tags if isinstance(tags, list) else []),
    }


def find_template_placeholders(html: str) -> list[str]:
    return sorted(set(re.findall(r"{{([a-zA-Z0-9_]+)}}", html)))
