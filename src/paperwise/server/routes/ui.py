from pathlib import Path
from html import escape
import json
import re

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse

from paperwise.application.interfaces import DocumentRepository
from paperwise.domain.models import DocumentStatus, LLMParseResult, User
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
_TABLE_BODY_RE_TEMPLATE = (
    r'(<tbody id="{element_id}"[^>]*>)'
    r'.*?'
    r'(</tbody>)'
)
_ACTIVITY_TOKEN_RE = re.compile(
    r'(<p id="activityTokenTotal" class="activity-token-total">)'
    r'.*?'
    r"(</p>)",
    re.DOTALL,
)


def _page_initial_data(current_user: User | None) -> dict:
    return {"authenticated": current_user is not None}


def _title_case_taxonomy_value(value: str) -> str:
    cleaned = " ".join(str(value or "").strip().split())
    if not cleaned:
        return cleaned
    words: list[str] = []
    for word in cleaned.split(" "):
        letters = "".join(ch for ch in word if ch.isalpha())
        if len(letters) >= 2 and letters.isupper():
            words.append(word)
        elif word.islower():
            words.append(word[:1].upper() + word[1:] if word else word)
        else:
            words.append(word)
    return " ".join(words)


def _document_list_item(repository: DocumentRepository, document_id: str) -> dict | None:
    document = repository.get(document_id)
    if document is None:
        return None
    llm_result = repository.get_llm_parse_result(document.id)
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


def _owner_llm_results(repository: DocumentRepository, current_user: User) -> list[LLMParseResult]:
    results: list[LLMParseResult] = []
    for document in repository.list_documents(limit=10_000):
        if document.owner_id != current_user.id:
            continue
        llm_result = repository.get_llm_parse_result(document.id)
        if llm_result is not None:
            results.append(llm_result)
    return results


def _tag_stats_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = _page_initial_data(current_user)
    if current_user is None:
        return {**initial_data, "tag_stats": []}
    counts: dict[str, int] = {}
    display_name_by_key: dict[str, str] = {}
    for llm_result in _owner_llm_results(repository, current_user):
        seen_tags: set[str] = set()
        for tag in llm_result.tags:
            cleaned = str(tag).strip()
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in seen_tags:
                continue
            seen_tags.add(key)
            display_name_by_key.setdefault(key, _title_case_taxonomy_value(cleaned))
            counts[key] = counts.get(key, 0) + 1
    return {
        **initial_data,
        "tag_stats": [
            {"tag": display_name_by_key[key], "document_count": count}
            for key, count in sorted(
                counts.items(),
                key=lambda item: (-item[1], display_name_by_key[item[0]].casefold()),
            )
        ],
    }


def _document_type_stats_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = _page_initial_data(current_user)
    if current_user is None:
        return {**initial_data, "document_type_stats": []}
    counts: dict[str, int] = {}
    display_name_by_key: dict[str, str] = {}
    for llm_result in _owner_llm_results(repository, current_user):
        cleaned = str(llm_result.document_type).strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        display_name_by_key.setdefault(key, _title_case_taxonomy_value(cleaned))
        counts[key] = counts.get(key, 0) + 1
    return {
        **initial_data,
        "document_type_stats": [
            {"document_type": display_name_by_key[key], "document_count": count}
            for key, count in sorted(
                counts.items(),
                key=lambda item: (-item[1], display_name_by_key[item[0]].casefold()),
            )
        ],
    }


def _activity_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = _page_initial_data(current_user)
    if current_user is None:
        return {**initial_data, "activity_documents": [], "activity_total_tokens": 0}
    ready_documents = [
        document
        for document in repository.list_documents(limit=20)
        if document.owner_id == current_user.id and document.status == DocumentStatus.READY
    ]
    preference = repository.get_user_preference(current_user.id)
    total_tokens = 0
    if preference is not None:
        total_tokens = int(preference.preferences.get("llm_total_tokens_processed") or 0)
    return {
        **initial_data,
        "activity_documents": [
            item
            for item in (_document_list_item(repository, document.id) for document in ready_documents)
            if item is not None
        ],
        "activity_total_tokens": total_tokens,
    }


def _pending_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = _page_initial_data(current_user)
    if current_user is None:
        return {**initial_data, "pending_documents": []}
    pending_documents = [
        document
        for document in repository.list_documents(limit=200)
        if document.owner_id == current_user.id and document.status != DocumentStatus.READY
    ]
    return {
        **initial_data,
        "pending_documents": [
            item
            for item in (_document_list_item(repository, document.id) for document in pending_documents)
            if item is not None
        ],
    }


def _replace_table_body(html: str, element_id: str, rows_html: str) -> str:
    pattern = re.compile(_TABLE_BODY_RE_TEMPLATE.format(element_id=re.escape(element_id)), re.DOTALL)
    return pattern.sub(rf"\1\n{rows_html}\n              \2", html, count=1)


def _tag_rows_html(tag_stats: list[dict]) -> str:
    if not tag_stats:
        return '                <tr><td colspan="3">No tags found.</td></tr>'
    rows: list[str] = []
    for stat in tag_stats:
        tag = escape(str(stat.get("tag") or ""))
        count = int(stat.get("document_count") or 0)
        rows.append(
            "                <tr>"
            f'<td data-label="Tag">{tag}</td>'
            f'<td data-label="Documents">{count}</td>'
            '<td data-label="Action"><div class="table-actions">'
            f'<a class="icon-action-button" href="/ui/documents?tag={tag}" title="View documents for tag {tag}">'
            '<span class="icon-action-label">View</span>'
            "</a>"
            "</div></td>"
            "</tr>"
        )
    return "\n".join(rows)


def _document_type_rows_html(type_stats: list[dict]) -> str:
    if not type_stats:
        return '                <tr><td colspan="3">No document types found.</td></tr>'
    rows: list[str] = []
    for stat in type_stats:
        document_type = escape(str(stat.get("document_type") or ""))
        count = int(stat.get("document_count") or 0)
        rows.append(
            "                <tr>"
            f'<td data-label="Document Type">{document_type}</td>'
            f'<td data-label="Documents">{count}</td>'
            '<td data-label="Action"><div class="table-actions">'
            f'<a class="icon-action-button" href="/ui/documents?document_type={document_type}" '
            f'title="View documents for type {document_type}">'
            '<span class="icon-action-label">View</span>'
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


def _activity_rows_html(documents: list[dict]) -> str:
    if not documents:
        return '                <tr><td colspan="4">No processed documents.</td></tr>'
    rows: list[str] = []
    for item in documents:
        document_id = escape(str(item.get("id") or ""))
        title = escape(_document_title(item))
        status_text = escape(str(item.get("status") or ""))
        created_at = escape(str(item.get("created_at") or "-"))
        rows.append(
            "                <tr>"
            f'<td data-label="Title"><a class="link-button" href="/ui/document?id={document_id}">{title}</a></td>'
            f'<td data-label="Status">{status_text}</td>'
            f'<td data-label="Uploaded">{created_at}</td>'
            '<td data-label="Action"><div class="table-actions">'
            f'<a class="icon-action-button" href="/ui/document?id={document_id}" title="Open document">'
            '<span class="icon-action-label">Open</span>'
            "</a>"
            "</div></td>"
            "</tr>"
        )
    return "\n".join(rows)


def _pending_rows_html(documents: list[dict]) -> str:
    if not documents:
        return '                <tr><td colspan="4">No pending documents.</td></tr>'
    rows: list[str] = []
    for item in documents:
        document_id = escape(str(item.get("id") or ""))
        title = escape(_document_title(item))
        status_text = escape(str(item.get("status") or ""))
        created_at = escape(str(item.get("created_at") or "-"))
        rows.append(
            f'                <tr data-pending-doc-id="{document_id}">'
            f'<td data-label="Title"><a class="link-button" href="/ui/document?id={document_id}">{title}</a></td>'
            f'<td data-label="Status">{status_text}</td>'
            f'<td data-label="Created">{created_at}</td>'
            '<td data-label="Action"><div class="table-actions">'
            f'<a class="icon-action-button" href="/ui/document?id={document_id}" title="Open document">'
            '<span class="icon-action-label">Open</span>'
            "</a>"
            "</div></td>"
            "</tr>"
        )
    return "\n".join(rows)


def _render_initial_page_data(html: str, initial_data: dict) -> str:
    if isinstance(initial_data.get("tag_stats"), list):
        html = _replace_table_body(html, "tagsTableBody", _tag_rows_html(initial_data["tag_stats"]))
    if isinstance(initial_data.get("document_type_stats"), list):
        html = _replace_table_body(
            html,
            "documentTypesTableBody",
            _document_type_rows_html(initial_data["document_type_stats"]),
        )
    if isinstance(initial_data.get("activity_documents"), list):
        html = _replace_table_body(
            html,
            "processedDocsTableBody",
            _activity_rows_html(initial_data["activity_documents"]),
        )
        total_tokens = int(initial_data.get("activity_total_tokens") or 0)
        html = _ACTIVITY_TOKEN_RE.sub(
            rf"\1LLM tokens processed: {total_tokens:,}\2",
            html,
            count=1,
        )
    if isinstance(initial_data.get("pending_documents"), list):
        html = _replace_table_body(
            html,
            "pendingTableBody",
            _pending_rows_html(initial_data["pending_documents"]),
        )
    return html


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
        html = _render_initial_page_data(html, initial_data)
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
def tags_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page("section-tags", initial_data=_tag_stats_initial_data(repository, current_user))


@router.get("/ui/document-types", include_in_schema=False)
def document_types_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page(
        "section-document-types",
        initial_data=_document_type_stats_initial_data(repository, current_user),
    )


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
def pending_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page("section-pending", initial_data=_pending_initial_data(repository, current_user))


@router.get("/ui/upload", include_in_schema=False)
def upload_page(current_user: User | None = Depends(optional_current_user_dependency)) -> HTMLResponse:
    return _render_ui_page("section-upload", initial_data=_page_initial_data(current_user))


@router.get("/ui/activity", include_in_schema=False)
def activity_page(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User | None = Depends(optional_current_user_dependency),
) -> HTMLResponse:
    return _render_ui_page("section-activity", initial_data=_activity_initial_data(repository, current_user))


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
