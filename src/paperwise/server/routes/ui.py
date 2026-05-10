from pathlib import Path
import json

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
from paperwise.application.services.llm_preferences import (
    llm_provider_defaults_payload,
    ocr_llm_provider_defaults_payload,
)
from paperwise.application.services.chat_threads import migrate_legacy_chat_threads
from paperwise.domain.models import Document, DocumentHistoryEvent, DocumentStatus, LLMParseResult, User
from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    optional_current_user_dependency,
)
from paperwise.server.html_rewriter import (
    render_active_nav,
    replace_activity_token_total,
    replace_element_html,
    replace_element_text,
    replace_input_value,
    replace_table_body,
)
from paperwise.server.routes.document_access import get_owned_document_or_404
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

router = APIRouter(tags=["ui"])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_STATIC_CSS_DIR = _STATIC_DIR / "css"
_STATIC_JS_DIR = _STATIC_DIR / "js"
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "ui"
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
PENDING_DOCUMENT_STATUSES = {
    DocumentStatus.RECEIVED,
    DocumentStatus.PROCESSING,
    DocumentStatus.FAILED,
}


def _page_initial_data(
    current_user: User | None,
    repository: DocumentRepository | None = None,
) -> dict:
    initial_data: dict = {
        "authenticated": current_user is not None,
        "ui_themes": list(SUPPORTED_UI_THEMES),
        "default_ui_theme": DEFAULT_UI_THEME,
        "llm_provider_defaults": llm_provider_defaults_payload(),
        "ocr_llm_provider_defaults": ocr_llm_provider_defaults_payload(),
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


def _document_list_item(document: Document, llm_result: LLMParseResult | None) -> dict:
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


def _tag_stats(repository: DocumentRepository, current_user: User) -> list[dict]:
    return [
        {"tag": tag, "document_count": count}
        for tag, count in repository.list_owner_tag_stats(current_user.id)
    ]


def _tag_stats_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = _page_initial_data(current_user, repository)
    if current_user is None:
        return {**initial_data, "tag_stats": []}
    return {**initial_data, "tag_stats": _tag_stats(repository, current_user)}


def _document_type_stats(repository: DocumentRepository, current_user: User) -> list[dict]:
    return [
        {"document_type": document_type, "document_count": count}
        for document_type, count in repository.list_owner_document_type_stats(current_user.id)
    ]


def _document_type_stats_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = _page_initial_data(current_user, repository)
    if current_user is None:
        return {**initial_data, "document_type_stats": []}
    return {
        **initial_data,
        "document_type_stats": _document_type_stats(repository, current_user),
    }


def _activity_documents(
    repository: DocumentRepository,
    current_user: User,
    *,
    limit: int,
) -> list[dict]:
    return [
        _document_list_item(document, llm_result)
        for document, llm_result in repository.list_owner_documents_with_llm_results(
            owner_id=current_user.id,
            limit=limit,
            statuses={DocumentStatus.READY},
        )
    ]


def _activity_total_tokens(repository: DocumentRepository, current_user: User) -> int:
    preference = repository.get_user_preference(current_user.id)
    if preference is not None:
        return int(preference.preferences.get("llm_total_tokens_processed") or 0)
    return 0


def _activity_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = _page_initial_data(current_user, repository)
    if current_user is None:
        return {**initial_data, "activity_documents": [], "activity_total_tokens": 0}
    return {
        **initial_data,
        "activity_documents": _activity_documents(repository, current_user, limit=20),
        "activity_total_tokens": _activity_total_tokens(repository, current_user),
    }


def _activity_partial_data(
    repository: DocumentRepository,
    current_user: User,
    *,
    limit: int = 20,
) -> dict:
    normalized_limit = min(100, max(1, int(limit or 20)))
    return {
        "activity_documents": _activity_documents(repository, current_user, limit=normalized_limit),
        "activity_total_tokens": _activity_total_tokens(repository, current_user),
    }


def _document_filter_options(repository: DocumentRepository, current_user: User) -> dict:
    return {
        "tags": [tag for tag, _count in repository.list_owner_tag_stats(current_user.id)],
        "correspondents": [
            correspondent
            for correspondent, _count in repository.list_owner_correspondent_stats(current_user.id)
        ],
        "document_types": [
            document_type
            for document_type, _count in repository.list_owner_document_type_stats(current_user.id)
        ],
        "statuses": ["received", "processing", "failed", "ready"],
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
    include_filter_options: bool = False,
) -> dict:
    initial_data = _page_initial_data(current_user, repository)
    normalized_page = max(1, int(page or 1))
    normalized_page_size = min(100, max(1, int(page_size or 20)))
    if current_user is None:
        data = {
            **initial_data,
            "documents": [],
            "documents_total": 0,
            "documents_processing_count": 0,
            "documents_page": normalized_page,
            "documents_page_size": normalized_page_size,
        }
        if include_filter_options:
            data["document_filter_options"] = {
                "tags": [],
                "correspondents": [],
                "document_types": [],
                "statuses": ["received", "processing", "failed", "ready"],
            }
        return data

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
    processing_count = repository.count_owner_documents_by_statuses(
        owner_id=current_user.id,
        statuses=PENDING_DOCUMENT_STATUSES,
    )
    data = {
        **initial_data,
        "documents": [
            _document_list_item(document, llm_result)
            for document, llm_result in matching_documents[offset : offset + normalized_page_size]
        ],
        "documents_total": documents_total,
        "documents_processing_count": processing_count,
        "documents_page": normalized_page,
        "documents_page_size": normalized_page_size,
    }
    if include_filter_options:
        data["document_filter_options"] = _document_filter_options(repository, current_user)
    return data


def _pending_documents(repository: DocumentRepository, current_user: User) -> list[dict]:
    return [
        _document_list_item(document, llm_result)
        for document, llm_result in repository.list_owner_documents_with_llm_results(
            owner_id=current_user.id,
            limit=200,
            statuses=PENDING_DOCUMENT_STATUSES,
        )
    ]


def _pending_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = _page_initial_data(current_user, repository)
    if current_user is None:
        return {**initial_data, "pending_documents": []}
    return {
        **initial_data,
        "pending_documents": _pending_documents(repository, current_user),
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
    item = _document_list_item(document, repository.get_llm_parse_result(document.id))
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


def _render_document_detail_data(html: str, initial_data: dict) -> str:
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
    for key, value in replacements.items():
        html = html.replace(f"{{{{{key}}}}}", value)
    return html


def _chat_thread_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    if current_user is None:
        return {**_page_initial_data(current_user, repository), "chat_threads": []}
    migrate_legacy_chat_threads(repository, current_user)
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
        "thread_list_html": chat_thread_list_html(
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
    script_names = ["shared.js", "app.js", *_PAGE_SCRIPTS_BY_VIEW.get(view_id, [])]
    asset_version = str(
        max(
            (_STATIC_CSS_DIR / "styles.css").stat().st_mtime_ns,
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
            include_filter_options=True,
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
            "table_body_html": document_rows_html(data["documents"]),
            "pagination_toolbar_html": documents_pagination_toolbar_html(
                total=data["documents_total"],
                processing_count=data["documents_processing_count"],
                page=data["documents_page"],
                page_size=data["documents_page_size"],
            ),
            "documents_returned": len(data["documents"]),
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
    tag_stats = _sort_stat_rows(
        _tag_stats(repository, current_user),
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return JSONResponse(
        {
            "table_body_html": tag_rows_html(tag_stats),
            "tag_count": len(tag_stats),
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
    document_type_stats = _sort_stat_rows(
        _document_type_stats(repository, current_user),
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    return JSONResponse(
        {
            "table_body_html": document_type_rows_html(document_type_stats),
            "document_type_count": len(document_type_stats),
        },
        headers={"Cache-Control": "no-store"},
    )


@router.get("/ui/partials/pending", include_in_schema=False)
def pending_partial(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> JSONResponse:
    pending_documents = _pending_documents(repository, current_user)
    return JSONResponse(
        {
            "table_body_html": pending_rows_html(pending_documents),
            "pending_count": len(pending_documents),
            "has_restartable_pending_documents": any(
                str(document.get("status") or "").strip().lower() not in {"", "ready"}
                for document in pending_documents
            ),
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
    activity_documents = data["activity_documents"]
    return JSONResponse(
        {
            "table_body_html": activity_rows_html(activity_documents),
            "activity_document_count": len(activity_documents),
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
        document_detail_fragments(data),
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
