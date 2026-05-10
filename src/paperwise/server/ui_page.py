from pathlib import Path
import json
import re

from fastapi.responses import HTMLResponse

from paperwise.server.html_rewriter import (
    render_active_nav,
    replace_activity_token_total,
    replace_element_html,
    replace_element_text,
    replace_input_value,
    replace_table_body,
)
from paperwise.server.ui_fragments import (
    activity_rows_html,
    chat_thread_list_html,
    document_detail_fragments,
    document_rows_html,
    document_type_rows_html,
    documents_pagination_toolbar_html,
    pending_rows_html,
    tag_rows_html,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
_STATIC_CSS_DIR = STATIC_DIR / "css"
_STATIC_JS_DIR = STATIC_DIR / "js"
_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates" / "ui"
_LAYOUT_TEMPLATE = _TEMPLATE_DIR / "layout.html"
_PARTIALS_DIR = _TEMPLATE_DIR / "partials"
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


def render_ui_page(
    view_id: str,
    *,
    page_name: str,
    initial_data: dict | None = None,
    active_nav_href: str | None = None,
) -> HTMLResponse:
    partial_name = _PAGE_PARTIAL_BY_NAME[page_name]
    html = _LAYOUT_TEMPLATE.read_text(encoding="utf-8")
    content = (_PARTIALS_DIR / partial_name).read_text(encoding="utf-8").rstrip()
    content = content.replace("{{theme_options}}", _theme_options_html())
    script_names = ["shared.js", "app.js", *_PAGE_SCRIPTS_BY_VIEW.get(view_id, [])]
    asset_version = str(
        max(
            *[path.stat().st_mtime_ns for path in _STATIC_CSS_DIR.glob("*.css")],
            *[(_STATIC_JS_DIR / script_name).stat().st_mtime_ns for script_name in script_names],
        )
    )
    asset_query = f"?v={asset_version}"
    page_script_tags = "\n".join(
        f'    <script src="/static/js/{script_name}{asset_query}" defer></script>'
        for script_name in script_names[2:]
    )
    html = _apply_layout_replacements(
        html,
        asset_query=asset_query,
        content=content,
        page_script_tags=page_script_tags,
        initial_data_script="{{initial_data_script}}",
    )
    html = render_active_nav(html, active_nav_href or _ACTIVE_NAV_BY_VIEW.get(view_id, "/ui/documents"))
    initial_data_script = ""
    if initial_data is not None:
        html = _render_initial_page_data(html, initial_data)
        if initial_data.get("authenticated") is True:
            html = _render_authenticated_html_class(html)
        payload = json.dumps(initial_data, ensure_ascii=True).replace("</", "<\\/")
        initial_data_script = (
            f'    <script id="paperwiseInitialData" type="application/json">{payload}</script>'
        )
    html = render_template_placeholders(
        html,
        {"initial_data_script": initial_data_script},
    )

    return HTMLResponse(
        html,
        headers={"Cache-Control": "no-store"},
    )


def _theme_options_html() -> str:
    return "\n".join(
        f'                      <option value="{theme}">{theme.replace("-", " ").title()}</option>'
        for theme in SUPPORTED_UI_THEMES
    )


def _render_document_detail_data(html: str, initial_data: dict) -> str:
    if not isinstance(initial_data.get("document_detail"), dict):
        return html
    fragments = document_detail_fragments(initial_data)
    if not fragments["document_id"]:
        return html
    for element_id, value in fragments["text"].items():
        html = replace_element_text(html, element_id, value)
    for element_id, value in fragments["html"].items():
        html = replace_element_html(html, element_id, value)
    for element_id, value in fragments["inputs"].items():
        html = replace_input_value(html, element_id, value)

    html = replace_element_html(html, "documentHistoryList", fragments["history_html"])
    return html


def _render_initial_page_data(html: str, initial_data: dict) -> str:
    html = _render_document_detail_data(html, initial_data)
    if isinstance(initial_data.get("documents"), list):
        html = replace_table_body(html, "docsTableBody", document_rows_html(initial_data["documents"]))
        total = int(initial_data.get("documents_total") or 0)
        processing_count = int(initial_data.get("documents_processing_count") or 0)
        page = max(1, int(initial_data.get("documents_page") or 1))
        page_size = max(1, int(initial_data.get("documents_page_size") or 20))
        html = replace_element_html(
            html,
            "documentsPaginationToolbar",
            documents_pagination_toolbar_html(
                total=total,
                processing_count=processing_count,
                page=page,
                page_size=page_size,
            ),
        )
    if isinstance(initial_data.get("tag_stats"), list):
        html = replace_table_body(html, "tagsTableBody", tag_rows_html(initial_data["tag_stats"]))
    if isinstance(initial_data.get("document_type_stats"), list):
        html = replace_table_body(
            html,
            "documentTypesTableBody",
            document_type_rows_html(initial_data["document_type_stats"]),
        )
    if isinstance(initial_data.get("activity_documents"), list):
        html = replace_table_body(
            html,
            "processedDocsTableBody",
            activity_rows_html(initial_data["activity_documents"]),
        )
        total_tokens = int(initial_data.get("activity_total_tokens") or 0)
        html = replace_activity_token_total(html, total_tokens)
    if isinstance(initial_data.get("pending_documents"), list):
        html = replace_table_body(
            html,
            "pendingTableBody",
            pending_rows_html(initial_data["pending_documents"]),
        )
    if isinstance(initial_data.get("chat_threads"), list):
        html = replace_element_html(
            html,
            "searchAskThreadList",
            chat_thread_list_html(initial_data["chat_threads"]),
        )
    return html


def _apply_layout_replacements(
    html: str,
    *,
    asset_query: str,
    content: str,
    page_script_tags: str,
    initial_data_script: str,
) -> str:
    replacements = {
        "asset_query": asset_query,
        "ui_theme_storage_key": UI_THEME_STORAGE_KEY,
        "supported_ui_themes_json": json.dumps(list(SUPPORTED_UI_THEMES)),
        "default_ui_theme": DEFAULT_UI_THEME,
        "page_scripts": page_script_tags,
        "content": content,
        "initial_data_script": initial_data_script,
    }
    return render_template_placeholders(html, replacements)


def render_template_placeholders(template: str, values: dict[str, object]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


def _render_authenticated_html_class(html: str) -> str:
    return html.replace('<html lang="en">', '<html lang="en" class="has-session">', 1)


def find_template_placeholders(html: str) -> list[str]:
    return sorted(set(re.findall(r"{{([a-zA-Z0-9_]+)}}", html)))
