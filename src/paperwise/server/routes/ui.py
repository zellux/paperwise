from pathlib import Path
import json
import re

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse

from paperwise.application.interfaces import DocumentRepository
from paperwise.domain.models import User
from paperwise.server.dependencies import (
    document_repository_dependency,
    optional_current_user_dependency,
)
from paperwise.server.routes.query import _migrate_legacy_chat_threads

router = APIRouter(tags=["ui"])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_VIEW_ARTICLE_RE = re.compile(
    r"\n\s*<article id=\"(?P<view_id>section-[^\"]+)\"(?P<attrs>[^>]*)>.*?\n\s*</article>",
    re.DOTALL,
)


def _page_initial_data(current_user: User | None) -> dict:
    return {"authenticated": current_user is not None}


def _chat_thread_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    if current_user is None:
        return {**_page_initial_data(current_user), "chat_threads": []}
    _migrate_legacy_chat_threads(repository, current_user)
    return {
        **_page_initial_data(current_user),
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
) -> HTMLResponse:
    html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    asset_version = str(
        max(
            (_STATIC_DIR / "app.js").stat().st_mtime_ns,
            (_STATIC_DIR / "styles.css").stat().st_mtime_ns,
        )
    )
    html = html.replace('/static/styles.css"', f'/static/styles.css?v={asset_version}"')
    html = html.replace('/static/app.js"', f'/static/app.js?v={asset_version}"')

    def keep_active_view(match: re.Match[str]) -> str:
        if match.group("view_id") != view_id:
            return ""
        return match.group(0).replace(" view-hidden", "", 1)

    html = _VIEW_ARTICLE_RE.sub(keep_active_view, html)
    if initial_data is not None:
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
def documents_page(current_user: User | None = Depends(optional_current_user_dependency)) -> HTMLResponse:
    return _render_ui_page("section-docs", initial_data=_page_initial_data(current_user))


@router.get("/ui/document", include_in_schema=False)
def document_page(current_user: User | None = Depends(optional_current_user_dependency)) -> HTMLResponse:
    return _render_ui_page("section-document", initial_data=_page_initial_data(current_user))


@router.get("/ui/tags", include_in_schema=False)
def tags_page(current_user: User | None = Depends(optional_current_user_dependency)) -> HTMLResponse:
    return _render_ui_page("section-tags", initial_data=_page_initial_data(current_user))


@router.get("/ui/document-types", include_in_schema=False)
def document_types_page(current_user: User | None = Depends(optional_current_user_dependency)) -> HTMLResponse:
    return _render_ui_page("section-document-types", initial_data=_page_initial_data(current_user))


@router.get("/ui/search", include_in_schema=False)
def search_page(current_user: User | None = Depends(optional_current_user_dependency)) -> HTMLResponse:
    return _render_ui_page("section-search", initial_data=_page_initial_data(current_user))


@router.get("/ui/grounded-qa", include_in_schema=False)
def grounded_qa_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-search",
        initial_data=_chat_thread_initial_data(repository, current_user),
    )


@router.get("/ui/pending", include_in_schema=False)
def pending_page(current_user: User | None = Depends(optional_current_user_dependency)) -> HTMLResponse:
    return _render_ui_page("section-pending", initial_data=_page_initial_data(current_user))


@router.get("/ui/upload", include_in_schema=False)
def upload_page(current_user: User | None = Depends(optional_current_user_dependency)) -> HTMLResponse:
    return _render_ui_page("section-upload", initial_data=_page_initial_data(current_user))


@router.get("/ui/activity", include_in_schema=False)
def activity_page(current_user: User | None = Depends(optional_current_user_dependency)) -> HTMLResponse:
    return _render_ui_page("section-activity", initial_data=_page_initial_data(current_user))


@router.get("/ui/settings", include_in_schema=False)
def settings_page(current_user: User | None = Depends(optional_current_user_dependency)) -> HTMLResponse:
    return _render_ui_page("section-settings", initial_data=_page_initial_data(current_user))


@router.get("/ui/settings/account", include_in_schema=False)
def settings_account_page(current_user: User | None = Depends(optional_current_user_dependency)) -> HTMLResponse:
    return _render_ui_page("section-settings", initial_data=_page_initial_data(current_user))


@router.get("/ui/settings/display", include_in_schema=False)
def settings_display_page(current_user: User | None = Depends(optional_current_user_dependency)) -> HTMLResponse:
    return _render_ui_page("section-settings", initial_data=_page_initial_data(current_user))


@router.get("/ui/settings/models", include_in_schema=False)
def settings_models_page(current_user: User | None = Depends(optional_current_user_dependency)) -> HTMLResponse:
    return _render_ui_page("section-settings", initial_data=_page_initial_data(current_user))


@router.get("/style-lab", include_in_schema=False)
def style_lab() -> FileResponse:
    return FileResponse(_STATIC_DIR / "style-lab.html")
