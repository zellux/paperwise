from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["ui"])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@router.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui/documents", status_code=307)


@router.get("/ui/documents", include_in_schema=False)
def documents_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@router.get("/ui/document", include_in_schema=False)
def document_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@router.get("/ui/tags", include_in_schema=False)
def tags_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@router.get("/ui/document-types", include_in_schema=False)
def document_types_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@router.get("/ui/search", include_in_schema=False)
def search_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@router.get("/ui/collections", include_in_schema=False)
def collections_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@router.get("/ui/grounded-qa", include_in_schema=False)
def grounded_qa_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@router.get("/ui/pending", include_in_schema=False)
def pending_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@router.get("/ui/upload", include_in_schema=False)
def upload_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@router.get("/ui/activity", include_in_schema=False)
def activity_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@router.get("/ui/settings", include_in_schema=False)
def settings_page() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


@router.get("/style-lab", include_in_schema=False)
def style_lab() -> FileResponse:
    return FileResponse(_STATIC_DIR / "style-lab.html")
