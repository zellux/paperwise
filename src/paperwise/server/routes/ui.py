from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse

from paperwise.application.interfaces import DocumentRepository
from paperwise.application.services.activity import owner_activity_summary
from paperwise.application.services.document_listing import (
    list_filtered_documents,
)
from paperwise.application.services.llm_preferences import (
    llm_supported_providers_payload,
    llm_provider_defaults_payload,
    ocr_supported_providers_payload,
    ocr_llm_provider_defaults_payload,
)
from paperwise.application.services.pending_documents import (
    PENDING_DOCUMENT_STATUSES,
    list_pending_documents,
)
from paperwise.application.services.chat_threads import migrate_legacy_chat_threads
from paperwise.application.services.taxonomy_stats import sort_stat_rows
from paperwise.application.services.user_preferences import load_normalized_user_preferences
from paperwise.domain.models import User
from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    optional_current_user_dependency,
)
from paperwise.server.document_access import get_owned_document_or_404
from paperwise.server.ui_payloads import document_list_item, history_event_item
from paperwise.server.ui_page import DEFAULT_UI_THEME, STATIC_DIR, SUPPORTED_UI_THEMES, render_ui_page
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


def _page_initial_data(
    current_user: User | None,
    repository: DocumentRepository | None = None,
) -> dict:
    initial_data: dict = {
        "authenticated": current_user is not None,
        "ui_themes": list(SUPPORTED_UI_THEMES),
        "default_ui_theme": DEFAULT_UI_THEME,
        "llm_supported_providers": llm_supported_providers_payload(),
        "ocr_supported_providers": ocr_supported_providers_payload(),
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
        initial_data["user_preferences"] = load_normalized_user_preferences(
            repository=repository,
            user_id=current_user.id,
        )
    return initial_data


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


def _activity_data(repository: DocumentRepository, current_user: User, *, limit: int) -> dict:
    summary = owner_activity_summary(
        repository=repository,
        owner_id=current_user.id,
        limit=limit,
    )
    return {
        "activity_documents": [
            document_list_item(document, llm_result)
            for document, llm_result in summary.documents
        ],
        "activity_total_tokens": summary.total_tokens,
    }


def _activity_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = _page_initial_data(current_user, repository)
    if current_user is None:
        return {**initial_data, "activity_documents": [], "activity_total_tokens": 0}
    return {
        **initial_data,
        **_activity_data(repository, current_user, limit=20),
    }


def _activity_partial_data(
    repository: DocumentRepository,
    current_user: User,
    *,
    limit: int = 20,
) -> dict:
    normalized_limit = min(100, max(1, int(limit or 20)))
    return _activity_data(repository, current_user, limit=normalized_limit)


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

    requested_offset = (normalized_page - 1) * normalized_page_size
    listing = list_filtered_documents(
        repository=repository,
        current_user=current_user,
        query=q,
        tag=tag,
        correspondent=correspondent,
        document_type=document_type,
        status=status,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=normalized_page_size,
        offset=requested_offset,
    )
    documents_total = listing.total
    total_pages = max(1, (documents_total + normalized_page_size - 1) // normalized_page_size)
    clamped_page = min(normalized_page, total_pages)
    if clamped_page != normalized_page:
        normalized_page = clamped_page
        listing = list_filtered_documents(
            repository=repository,
            current_user=current_user,
            query=q,
            tag=tag,
            correspondent=correspondent,
            document_type=document_type,
            status=status,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=normalized_page_size,
            offset=(normalized_page - 1) * normalized_page_size,
        )
    processing_count = repository.count_owner_documents_by_statuses(
        owner_id=current_user.id,
        statuses=PENDING_DOCUMENT_STATUSES,
    )
    data = {
        **initial_data,
        "documents": [
            document_list_item(document, llm_result)
            for document, llm_result in listing.rows
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
        document_list_item(document, llm_result)
        for document, llm_result in list_pending_documents(
            repository=repository,
            owner_id=current_user.id,
            limit=200,
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
    item = document_list_item(document, repository.get_llm_parse_result(document.id))
    return {
        **initial_data,
        "document_detail": {
            "document": item,
            "ocr_text_preview": parse_result.text_preview if parse_result is not None else None,
            "ocr_parsed_at": parse_result.created_at.isoformat() if parse_result is not None else None,
        },
        "document_history": [
            history_event_item(event)
            for event in repository.list_history(document_id=document.id, limit=100)
        ],
    }


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
    return render_ui_page(
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
    return render_ui_page(
        "section-document",
        page_name="document",
        initial_data=_document_detail_initial_data(repository, current_user, id),
    )


@router.get("/ui/tags", include_in_schema=False)
def tags_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-tags",
        page_name="tags",
        initial_data=_tag_stats_initial_data(repository, current_user),
    )


@router.get("/ui/document-types", include_in_schema=False)
def document_types_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-document-types",
        page_name="document-types",
        initial_data=_document_type_stats_initial_data(repository, current_user),
    )


@router.get("/ui/search", include_in_schema=False)
def search_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-search",
        page_name="search",
        initial_data=_page_initial_data(current_user, repository),
    )


@router.get("/ui/grounded-qa", include_in_schema=False)
def grounded_qa_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
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
    return render_ui_page(
        "section-pending",
        page_name="pending",
        initial_data=_pending_initial_data(repository, current_user),
    )


@router.get("/ui/upload", include_in_schema=False)
def upload_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-upload",
        page_name="upload",
        initial_data=_page_initial_data(current_user, repository),
    )


@router.get("/ui/activity", include_in_schema=False)
def activity_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-activity",
        page_name="activity",
        initial_data=_activity_initial_data(repository, current_user),
    )


@router.get("/ui/settings", include_in_schema=False)
def settings_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-settings",
        page_name="settings-display",
        initial_data=_page_initial_data(current_user, repository),
    )


@router.get("/ui/settings/account", include_in_schema=False)
def settings_account_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-settings",
        page_name="settings-account",
        initial_data=_page_initial_data(current_user, repository),
    )


@router.get("/ui/settings/display", include_in_schema=False)
def settings_display_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-settings",
        page_name="settings-display",
        initial_data=_page_initial_data(current_user, repository),
    )


@router.get("/ui/settings/models", include_in_schema=False)
def settings_models_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
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
    tag_stats = sort_stat_rows(
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
    document_type_stats = sort_stat_rows(
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
    return FileResponse(STATIC_DIR / "style-lab.html")
