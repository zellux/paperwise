from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse

from paperwise.application.interfaces import DocumentRepository
from paperwise.application.services.taxonomy_stats import sort_stat_rows
from paperwise.domain.models import User
from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    optional_current_user_dependency,
)
from paperwise.server.ui_initial_data import (
    activity_initial_data,
    activity_partial_data,
    chat_thread_initial_data,
    chat_threads_partial_data,
    document_detail_initial_data,
    document_type_stats as build_document_type_stats,
    document_type_stats_initial_data,
    documents_initial_data,
    page_initial_data,
    pending_documents as build_pending_documents,
    pending_initial_data,
    tag_stats as build_tag_stats,
    tag_stats_initial_data,
)
from paperwise.server.ui_page import STATIC_DIR, render_ui_page
from paperwise.server.ui_fragments import (
    activity_rows_html,
    document_detail_fragments,
    document_rows_html,
    document_type_rows_html,
    documents_pagination_toolbar_html,
    pending_rows_html,
    tag_rows_html,
)

router = APIRouter(tags=["ui"])


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
        initial_data=documents_initial_data(
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
        initial_data=document_detail_initial_data(repository, current_user, id),
    )


@router.get("/ui/tags", include_in_schema=False)
def tags_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-tags",
        page_name="tags",
        initial_data=tag_stats_initial_data(repository, current_user),
    )


@router.get("/ui/document-types", include_in_schema=False)
def document_types_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-document-types",
        page_name="document-types",
        initial_data=document_type_stats_initial_data(repository, current_user),
    )


@router.get("/ui/search", include_in_schema=False)
def search_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-search",
        page_name="search",
        initial_data=page_initial_data(current_user, repository),
    )


@router.get("/ui/grounded-qa", include_in_schema=False)
def grounded_qa_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-search",
        page_name="grounded-qa",
        initial_data=chat_thread_initial_data(repository, current_user),
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
        initial_data=pending_initial_data(repository, current_user),
    )


@router.get("/ui/upload", include_in_schema=False)
def upload_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-upload",
        page_name="upload",
        initial_data=page_initial_data(current_user, repository),
    )


@router.get("/ui/activity", include_in_schema=False)
def activity_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-activity",
        page_name="activity",
        initial_data=activity_initial_data(repository, current_user),
    )


@router.get("/ui/settings", include_in_schema=False)
def settings_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-settings",
        page_name="settings-display",
        initial_data=page_initial_data(current_user, repository),
    )


@router.get("/ui/settings/account", include_in_schema=False)
def settings_account_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-settings",
        page_name="settings-account",
        initial_data=page_initial_data(current_user, repository),
    )


@router.get("/ui/settings/display", include_in_schema=False)
def settings_display_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-settings",
        page_name="settings-display",
        initial_data=page_initial_data(current_user, repository),
    )


@router.get("/ui/settings/models", include_in_schema=False)
def settings_models_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return render_ui_page(
        "section-settings",
        page_name="settings-models",
        initial_data=page_initial_data(current_user, repository),
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
    data = documents_initial_data(
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
        build_tag_stats(repository, current_user),
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
        build_document_type_stats(repository, current_user),
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
    pending_documents = build_pending_documents(repository, current_user)
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
    data = activity_partial_data(repository, current_user, limit=limit)
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
    data = document_detail_initial_data(repository, current_user, id)
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
        chat_threads_partial_data(
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
