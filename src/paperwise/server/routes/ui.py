from pathlib import Path
import re

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["ui"])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_VIEW_ARTICLE_RE = re.compile(
    r"\n\s*<article id=\"(?P<view_id>section-[^\"]+)\"(?P<attrs>[^>]*)>.*?\n\s*</article>",
    re.DOTALL,
)


def _render_ui_page(view_id: str) -> HTMLResponse:
    html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")

    def keep_active_view(match: re.Match[str]) -> str:
        if match.group("view_id") != view_id:
            return ""
        return match.group(0).replace(" view-hidden", "", 1)

    return HTMLResponse(_VIEW_ARTICLE_RE.sub(keep_active_view, html))


@router.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui/documents", status_code=307)


@router.get("/ui/documents", include_in_schema=False)
def documents_page() -> HTMLResponse:
    return _render_ui_page("section-docs")


@router.get("/ui/document", include_in_schema=False)
def document_page() -> HTMLResponse:
    return _render_ui_page("section-document")


@router.get("/ui/tags", include_in_schema=False)
def tags_page() -> HTMLResponse:
    return _render_ui_page("section-tags")


@router.get("/ui/document-types", include_in_schema=False)
def document_types_page() -> HTMLResponse:
    return _render_ui_page("section-document-types")


@router.get("/ui/search", include_in_schema=False)
def search_page() -> HTMLResponse:
    return _render_ui_page("section-search")


@router.get("/ui/collections", include_in_schema=False)
def collections_page() -> HTMLResponse:
    return _render_ui_page("section-search")


@router.get("/ui/grounded-qa", include_in_schema=False)
def grounded_qa_page() -> HTMLResponse:
    return _render_ui_page("section-search")


@router.get("/ui/pending", include_in_schema=False)
def pending_page() -> HTMLResponse:
    return _render_ui_page("section-pending")


@router.get("/ui/upload", include_in_schema=False)
def upload_page() -> HTMLResponse:
    return _render_ui_page("section-upload")


@router.get("/ui/activity", include_in_schema=False)
def activity_page() -> HTMLResponse:
    return _render_ui_page("section-activity")


@router.get("/ui/settings", include_in_schema=False)
def settings_page() -> HTMLResponse:
    return _render_ui_page("section-settings")


@router.get("/ui/settings/account", include_in_schema=False)
def settings_account_page() -> HTMLResponse:
    return _render_ui_page("section-settings")


@router.get("/ui/settings/display", include_in_schema=False)
def settings_display_page() -> HTMLResponse:
    return _render_ui_page("section-settings")


@router.get("/ui/settings/models", include_in_schema=False)
def settings_models_page() -> HTMLResponse:
    return _render_ui_page("section-settings")


@router.get("/style-lab", include_in_schema=False)
def style_lab() -> FileResponse:
    return FileResponse(_STATIC_DIR / "style-lab.html")
