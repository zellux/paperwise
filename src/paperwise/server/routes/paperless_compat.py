"""Thin Paperless-ngx API adapter for Paperless Mobile.

This module intentionally does not implement Paperless-ngx semantics wholesale.
It translates the subset of request/response shapes used by Paperless Mobile
onto Paperwise's native document, user, and taxonomy model. Keep compatibility
behavior isolated here so the native Paperwise API can evolve independently.
"""

import json
import re
import zlib
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from paperwise.application.interfaces import DocumentRepository, IngestionDispatcher, StorageProvider, UserRepository
from paperwise.application.services.documents import CreateDocumentCommand, create_document
from paperwise.application.services.filenames import sanitize_storage_filename
from paperwise.application.services.metadata_updates import update_document_metadata, validate_document_date
from paperwise.application.services.session_tokens import create_session_token, decode_session_token
from paperwise.application.services.upload_validation import is_supported_upload, normalize_content_type
from paperwise.application.services.users import authenticate_user
from paperwise.application.services.document_file_cleanup import resolve_file_path_from_uri
from paperwise.domain.models import Document, HistoryActorType, LLMParseResult, User
from paperwise.infrastructure.config import Settings
from paperwise.server.dependencies import (
    document_repository_dependency,
    ingestion_dispatcher_dependency,
    settings_dependency,
    storage_dependency,
)


router = APIRouter(prefix="/api", tags=["paperless-compat"])

API_VERSION = "9"
DEFAULT_PAGE_SIZE = 25
MAX_COMPAT_ROWS = 10_000


def _int_alias(namespace: str, value: str) -> int:
    alias = zlib.crc32(f"{namespace}:{value}".encode("utf-8")) & 0x7FFFFFFF
    return alias or 1


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "untitled"


def _paperless_headers(response: Response) -> None:
    response.headers["x-api-version"] = API_VERSION


def _current_user_from_token(
    authorization: str | None = Header(default=None),
    repository: UserRepository = Depends(document_repository_dependency),
    settings: Settings = Depends(settings_dependency),
) -> User:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "token" or not token.strip():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    payload = decode_session_token(token=token.strip(), secret=settings.auth_secret)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = repository.get_user(str(payload.get("sub")))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return user


def _user_id(user: User) -> int:
    return _int_alias("user", user.id)


def _user_payload(user: User) -> dict[str, Any]:
    name_parts = user.full_name.strip().split()
    return {
        "id": _user_id(user),
        "username": user.email,
        "email": user.email,
        "first_name": name_parts[0] if name_parts else "",
        "last_name": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
        "date_joined": user.created_at.isoformat(),
        "is_staff": False,
        "is_active": user.is_active,
        "is_superuser": False,
        "groups": [],
        "user_permissions": [],
        "inherited_permissions": [],
        "is_mfa_enabled": False,
    }


def _owner_rows(
    repository: DocumentRepository,
    user: User,
    *,
    limit: int = MAX_COMPAT_ROWS,
    offset: int = 0,
) -> list[tuple[Document, LLMParseResult | None]]:
    return repository.list_owner_documents_with_llm_results(owner_id=user.id, limit=limit, offset=offset)


def _resolve_document(
    document_id: int,
    repository: DocumentRepository,
    user: User,
) -> tuple[Document, LLMParseResult | None]:
    for document, llm_result in _owner_rows(repository, user):
        if _int_alias("document", document.id) == document_id:
            return document, llm_result
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")


def _taxonomy_names(repository: DocumentRepository, kind: str) -> list[str]:
    if kind == "correspondent":
        return repository.list_correspondents()
    if kind == "document_type":
        return repository.list_document_types()
    if kind == "tag":
        return repository.list_tags()
    if kind == "storage_path":
        return []
    raise ValueError(f"Unsupported taxonomy kind: {kind}")


def _taxonomy_id(kind: str, name: str) -> int:
    return _int_alias(kind, name.strip().casefold())


def _label_payload(kind: str, name: str, document_count: int = 0, owner_id: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": _taxonomy_id(kind, name),
        "name": name,
        "slug": _slug(name),
        "match": "",
        "matching_algorithm": 6,
        "is_insensitive": True,
        "document_count": document_count,
        "owner": owner_id,
        "user_can_change": True,
    }
    if kind == "storage_path":
        payload["path"] = ""
    return payload


def _stats_map(repository: DocumentRepository, user: User, kind: str) -> dict[str, int]:
    if kind == "tag":
        return dict(repository.list_owner_tag_stats(user.id))
    if kind == "document_type":
        return dict(repository.list_owner_document_type_stats(user.id))
    if kind == "correspondent":
        return dict(repository.list_owner_correspondent_stats(user.id))
    return {}


def _resolve_taxonomy_name(
    repository: DocumentRepository,
    kind: str,
    label_id: int | None,
    fallback: str,
) -> str:
    if label_id is None:
        return fallback
    for name in _taxonomy_names(repository, kind):
        if _taxonomy_id(kind, name) == label_id:
            return name
    return fallback


def _resolve_tag_names(repository: DocumentRepository, tag_ids: list[int] | None) -> list[str]:
    if tag_ids is None:
        return []
    names = []
    for name in repository.list_tags():
        if _taxonomy_id("tag", name) in tag_ids:
            names.append(name)
    return names


def _document_title(document: Document, llm_result: LLMParseResult | None) -> str:
    if llm_result is not None and llm_result.suggested_title.strip():
        return llm_result.suggested_title
    return Path(document.filename).stem or document.filename


def _document_content(repository: DocumentRepository, document_id: str) -> str:
    parse_result = repository.get_parse_result(document_id)
    return parse_result.text_preview if parse_result is not None else ""


def _document_payload(
    document: Document,
    llm_result: LLMParseResult | None,
    repository: DocumentRepository,
    *,
    include_content: bool = False,
) -> dict[str, Any]:
    created = document.created_at.isoformat()
    document_type_id = _taxonomy_id("document_type", llm_result.document_type) if llm_result else None
    correspondent_id = _taxonomy_id("correspondent", llm_result.correspondent) if llm_result else None
    tag_ids = [_taxonomy_id("tag", tag) for tag in llm_result.tags] if llm_result else []
    parse_result = repository.get_parse_result(document.id)
    payload: dict[str, Any] = {
        "id": _int_alias("document", document.id),
        "correspondent": correspondent_id,
        "document_type": document_type_id,
        "storage_path": None,
        "title": _document_title(document, llm_result),
        "tags": tag_ids,
        "created": f"{llm_result.document_date}T00:00:00Z" if llm_result and llm_result.document_date else created,
        "created_date": f"{llm_result.document_date}T00:00:00Z" if llm_result and llm_result.document_date else created,
        "modified": created,
        "added": created,
        "deleted_at": None,
        "archive_serial_number": None,
        "original_file_name": document.filename,
        "archived_file_name": document.filename,
        "owner": _int_alias("user", document.owner_id),
        "permissions": None,
        "user_can_change": True,
        "is_shared_by_requester": False,
        "notes": [],
        "custom_fields": [],
        "page_count": parse_result.page_count if parse_result is not None else None,
        "mime_type": document.content_type,
    }
    if include_content:
        payload["content"] = _document_content(repository, document.id)
    return payload


def _paginated(
    request_path: str,
    *,
    count: int,
    page: int,
    page_size: int,
    results: list[dict[str, Any]],
    all_ids: list[int] | None = None,
) -> dict[str, Any]:
    next_url = None
    previous_url = None
    if page * page_size < count:
        next_url = f"{request_path}?page={page + 1}&page_size={page_size}"
    if page > 1:
        previous_url = f"{request_path}?page={page - 1}&page_size={page_size}"
    return {
        "count": count,
        "next": next_url,
        "previous": previous_url,
        "all": all_ids,
        "results": results,
    }


def _split_ints(value: str | None) -> list[int]:
    if not value:
        return []
    ids: list[int] = []
    for item in value.split(","):
        try:
            ids.append(int(item.strip()))
        except ValueError:
            continue
    return ids


def _parse_int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _matches_query(document: Document, llm_result: LLMParseResult | None, query: str | None, repository: DocumentRepository) -> bool:
    if not query:
        return True
    haystack = " ".join(
        [
            document.filename,
            _document_title(document, llm_result),
            llm_result.correspondent if llm_result else "",
            llm_result.document_type if llm_result else "",
            " ".join(llm_result.tags) if llm_result else "",
            _document_content(repository, document.id),
        ]
    ).casefold()
    return query.casefold() in haystack


def _filter_rows(
    rows: list[tuple[Document, LLMParseResult | None]],
    repository: DocumentRepository,
    *,
    query: str | None,
    title__icontains: str | None,
    correspondent__id: int | None,
    document_type__id: int | None,
    tags__id__all: str | None,
    tags__id__in: str | None,
    id__in: str | None,
) -> list[tuple[Document, LLMParseResult | None]]:
    required_tags = set(_split_ints(tags__id__all))
    any_tags = set(_split_ints(tags__id__in))
    document_ids = set(_split_ints(id__in))
    filtered = []
    for document, llm_result in rows:
        payload_id = _int_alias("document", document.id)
        if document_ids and payload_id not in document_ids:
            continue
        if correspondent__id is not None and (llm_result is None or _taxonomy_id("correspondent", llm_result.correspondent) != correspondent__id):
            continue
        if document_type__id is not None and (llm_result is None or _taxonomy_id("document_type", llm_result.document_type) != document_type__id):
            continue
        tag_ids = {_taxonomy_id("tag", tag) for tag in llm_result.tags} if llm_result else set()
        if required_tags and not required_tags.issubset(tag_ids):
            continue
        if any_tags and not any_tags.intersection(tag_ids):
            continue
        if title__icontains and title__icontains.casefold() not in _document_title(document, llm_result).casefold():
            continue
        if not _matches_query(document, llm_result, query, repository):
            continue
        filtered.append((document, llm_result))
    return filtered


def _sort_rows(
    rows: list[tuple[Document, LLMParseResult | None]],
    ordering: str | None,
) -> list[tuple[Document, LLMParseResult | None]]:
    reverse = True
    field = ordering or "-created"
    if field.startswith("-"):
        field = field[1:]
        reverse = True
    else:
        reverse = False
    if field in {"title"}:
        return sorted(rows, key=lambda row: _document_title(row[0], row[1]).casefold(), reverse=reverse)
    if field in {"correspondent__name"}:
        return sorted(rows, key=lambda row: (row[1].correspondent if row[1] else "").casefold(), reverse=reverse)
    if field in {"document_type__name"}:
        return sorted(rows, key=lambda row: (row[1].document_type if row[1] else "").casefold(), reverse=reverse)
    return sorted(rows, key=lambda row: row[0].created_at, reverse=reverse)


@router.post("/token/")
def create_token(
    payload: dict[str, Any],
    repository: UserRepository = Depends(document_repository_dependency),
    settings: Settings = Depends(settings_dependency),
) -> dict[str, str]:
    user = authenticate_user(
        email=str(payload.get("username", "")),
        password=str(payload.get("password", "")),
        repository=repository,
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to log in with provided credentials.")
    token = create_session_token(user_id=user.id, secret=settings.auth_secret, ttl_seconds=settings.session_ttl_seconds)
    return {"token": token}


@router.head("/schema/")
def head_schema(response: Response) -> None:
    _paperless_headers(response)


@router.get("/schema/")
def get_schema(response: Response) -> dict[str, Any]:
    _paperless_headers(response)
    return {"openapi": "3.0.0", "info": {"title": "Paperwise Paperless compatibility API", "version": API_VERSION}}


@router.head("/profile/")
def head_profile(
    response: Response,
    current_user: User = Depends(_current_user_from_token),
) -> None:
    del current_user
    _paperless_headers(response)


@router.get("/profile/")
def get_profile(
    response: Response,
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    _paperless_headers(response)
    name_parts = current_user.full_name.strip().split()
    return {
        "email": current_user.email,
        "first_name": name_parts[0] if name_parts else "",
        "last_name": " ".join(name_parts[1:]) if len(name_parts) > 1 else "",
        "auth_token": None,
        "has_usable_password": True,
        "social_accounts": [],
        "is_mfa_enabled": False,
    }


@router.get("/ui_settings/")
def get_ui_settings(
    response: Response,
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    _paperless_headers(response)
    return {
        "permissions": [],
        "settings": {
            "version": "0.0.0",
            "app_logo": "",
            "app_title": "Paperwise",
            "trash_delay": 0,
            "email_enabled": False,
            "tour_complete": True,
            "auditlog_enabled": False,
            "update_checking": {"backend_setting": False},
            "permissions": {
                "default_owner": _user_id(current_user),
                "default_edit_users": [],
                "default_view_users": [],
                "default_edit_groups": [],
                "default_view_groups": [],
            },
            "date_display": {"date_format": "mediumDate", "date_locale": None},
            "search": {"more_link": "title-content"},
            "saved_views": {"dashboard_views_sort_order": []},
        },
        "user": {
            "id": _user_id(current_user),
            "username": current_user.email,
            "first_name": current_user.full_name,
            "last_name": "",
            "groups": [],
            "is_staff": False,
            "is_superuser": False,
        },
    }


@router.get("/users/{user_id}/")
def get_user(
    user_id: int,
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    if user_id != _user_id(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_payload(current_user)


@router.patch("/users/{user_id}/")
def patch_user(
    user_id: int,
    payload: dict[str, Any],
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    del payload
    if user_id != _user_id(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_payload(current_user)


@router.put("/users/{user_id}/")
def put_user(
    user_id: int,
    payload: dict[str, Any],
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    return patch_user(user_id, payload, current_user)


@router.post("/users/{user_id}/deactivate_totp/")
def deactivate_totp(
    user_id: int,
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, str]:
    if user_id != _user_id(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"detail": "TOTP is not enabled for this Paperwise compatibility user."}


@router.get("/users/")
def list_users(
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    payload = _user_payload(current_user)
    return _paginated("/api/users/", count=1, page=1, page_size=1, results=[payload], all_ids=[payload["id"]])


@router.get("/statistics/")
def statistics(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    rows = _owner_rows(repository, current_user)
    mime_counts: dict[str, int] = {}
    for document, _ in rows:
        mime_counts[document.content_type] = mime_counts.get(document.content_type, 0) + 1
    return {
        "documents_total": len(rows),
        "documents_inbox": 0,
        "inbox_tag": None,
        "inbox_tags": [],
        "tag_count": len(repository.list_tags()),
        "correspondent_count": len(repository.list_correspondents()),
        "document_type_count": len(repository.list_document_types()),
        "storage_path_count": 0,
        "current_asn": None,
        "document_file_type_counts": [
            {"mime_type": mime_type, "mime_type_count": count} for mime_type, count in sorted(mime_counts.items())
        ],
        "character_count": sum(len(_document_content(repository, document.id)) for document, _ in rows),
    }


@router.get("/remote_version/")
def remote_version(response: Response) -> dict[str, Any]:
    response.headers["x-version"] = "0.0.0"
    return {"version": "0.0.0", "update_available": False}


@router.get("/documents/")
def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1),
    ordering: str | None = Query(None),
    query: str | None = Query(None),
    title__icontains: str | None = Query(None),
    correspondent__id: int | None = Query(None),
    document_type__id: int | None = Query(None),
    tags__id__all: str | None = Query(None),
    tags__id__in: str | None = Query(None),
    id__in: str | None = Query(None),
    truncate_content: bool = Query(True),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    del truncate_content
    rows = _sort_rows(
        _filter_rows(
            _owner_rows(repository, current_user),
            repository,
            query=query,
            title__icontains=title__icontains,
            correspondent__id=correspondent__id,
            document_type__id=document_type__id,
            tags__id__all=tags__id__all,
            tags__id__in=tags__id__in,
            id__in=id__in,
        ),
        ordering,
    )
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]
    return _paginated(
        "/api/documents/",
        count=len(rows),
        page=page,
        page_size=page_size,
        all_ids=[_int_alias("document", document.id) for document, _ in rows],
        results=[
            _document_payload(document, llm_result, repository, include_content=False)
            for document, llm_result in page_rows
        ],
    )


@router.post("/documents/post_document/")
def post_document(
    document: UploadFile = File(...),
    title: str | None = Form(None),
    created: str | None = Form(None),
    correspondent: str | None = Form(None),
    document_type: str | None = Form(None),
    tags: list[str] | None = Form(None),
    repository: DocumentRepository = Depends(document_repository_dependency),
    dispatcher: IngestionDispatcher = Depends(ingestion_dispatcher_dependency),
    storage: StorageProvider = Depends(storage_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> str:
    filename = document.filename or "uploaded-document"
    normalized_content_type = normalize_content_type(document.content_type) or "application/octet-stream"
    if not is_supported_upload(filename=filename, content_type=normalized_content_type):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported upload type.")
    content = document.file.read()
    checksum = sha256(content).hexdigest()
    existing = repository.get_by_owner_checksum(current_user.id, checksum)
    if existing is not None:
        return existing.id
    now = datetime.now(UTC)
    date_path = now.strftime("%Y/%m/%d")
    storage_token = str(uuid4())
    storage_basename = sanitize_storage_filename(filename, reserved_prefix=f"{storage_token}_")
    storage_key = f"incoming/{date_path}/{storage_token}_{storage_basename}"
    blob_uri = storage.put(key=storage_key, data=content, content_type=normalized_content_type)
    storage.put(
        key=f"incoming/{date_path}/{storage_token}.metadata.json",
        data=json.dumps({"original_filename": filename, "content_type": normalized_content_type}, ensure_ascii=True).encode("utf-8"),
        content_type="application/json",
    )
    created_document, job_id = create_document(
        CreateDocumentCommand(
            filename=filename,
            owner_id=current_user.id,
            blob_uri=blob_uri,
            checksum_sha256=checksum,
            content_type=normalized_content_type,
            size_bytes=len(content),
        ),
        repository=repository,
        dispatcher=dispatcher,
    )
    if title or created or correspondent or document_type or tags:
        tag_ids = [_parse_int(tag) for tag in tags or []]
        tag_names = _resolve_tag_names(repository, [tag_id for tag_id in tag_ids if tag_id is not None])
        tag_names.extend(
            str(tag).strip()
            for tag, tag_id in zip(tags or [], tag_ids, strict=False)
            if tag_id is None and str(tag).strip()
        )
        update_document_metadata(
            document=created_document,
            suggested_title=title or Path(filename).stem,
            document_date=validate_document_date(created),
            correspondent=_resolve_taxonomy_name(
                repository,
                "correspondent",
                _parse_int(correspondent),
                correspondent or "Unknown Sender",
            ),
            document_type=_resolve_taxonomy_name(
                repository,
                "document_type",
                _parse_int(document_type),
                document_type or "General Document",
            ),
            tags=tag_names,
            repository=repository,
            actor_type=HistoryActorType.USER,
            actor_id=current_user.id,
            history_source="paperless_compat_upload",
        )
    return job_id


@router.get("/documents/next_asn/")
def next_asn(current_user: User = Depends(_current_user_from_token)) -> int:
    del current_user
    return 0


@router.post("/documents/bulk_edit/")
def bulk_edit(payload: dict[str, Any], current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    del current_user
    return {"result": "OK", "document_ids": payload.get("documents", [])}


@router.post("/documents/bulk_download/")
def bulk_download(payload: dict[str, Any], current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    del current_user
    return {"content": "", "filename": "paperwise-documents.zip"}


@router.post("/documents/selection_data/")
def selection_data(payload: dict[str, Any], current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    del current_user
    document_ids = payload.get("document_ids") if isinstance(payload, dict) else []
    return {
        "selected_correspondents": [],
        "selected_tags": [],
        "selected_document_types": [],
        "selected_storage_paths": [],
        "documents": document_ids or [],
    }


@router.get("/documents/{document_id}/")
def get_document(
    document_id: int,
    fields: str | None = Query(None),
    full_perms: bool = Query(False),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    del fields, full_perms
    document, llm_result = _resolve_document(document_id, repository, current_user)
    return _document_payload(document, llm_result, repository, include_content=True)


@router.patch("/documents/{document_id}/")
def patch_document(
    document_id: int,
    payload: dict[str, Any],
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    document, llm_result = _resolve_document(document_id, repository, current_user)
    current_title = _document_title(document, llm_result)
    current_date = llm_result.document_date if llm_result is not None else None
    correspondent_name = _resolve_taxonomy_name(repository, "correspondent", payload.get("correspondent"), llm_result.correspondent if llm_result else "Unknown Sender")
    document_type_name = _resolve_taxonomy_name(repository, "document_type", payload.get("document_type"), llm_result.document_type if llm_result else "General Document")
    if "tags" in payload:
        tag_names = _resolve_tag_names(repository, payload.get("tags") or [])
    else:
        tag_names = list(llm_result.tags) if llm_result is not None else []
    result = update_document_metadata(
        document=document,
        suggested_title=str(payload.get("title") or current_title),
        document_date=validate_document_date(payload.get("created")) or current_date,
        correspondent=correspondent_name,
        document_type=document_type_name,
        tags=tag_names,
        repository=repository,
        actor_type=HistoryActorType.USER,
        actor_id=current_user.id,
        history_source="paperless_compat_patch",
    )
    return _document_payload(document, result, repository, include_content=True)


@router.put("/documents/{document_id}/")
def put_document(
    document_id: int,
    payload: dict[str, Any],
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    return patch_document(document_id, payload, repository, current_user)


@router.delete("/documents/{document_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> None:
    document, _ = _resolve_document(document_id, repository, current_user)
    repository.delete_document(document.id)


@router.get("/documents/{document_id}/download/")
def download_document(
    document_id: int,
    repository: DocumentRepository = Depends(document_repository_dependency),
    settings: Settings = Depends(settings_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> FileResponse:
    document, _ = _resolve_document(document_id, repository, current_user)
    file_path = resolve_file_path_from_uri(document.blob_uri, settings.object_store_root)
    if file_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file not found")
    return FileResponse(path=file_path, media_type=document.content_type or "application/octet-stream", filename=document.filename)


@router.get("/documents/{document_id}/preview/")
def preview_document(
    document_id: int,
    repository: DocumentRepository = Depends(document_repository_dependency),
    settings: Settings = Depends(settings_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> FileResponse:
    return download_document(document_id, repository, settings, current_user)


@router.get("/documents/{document_id}/thumb/")
def thumb_document(
    document_id: int,
    repository: DocumentRepository = Depends(document_repository_dependency),
    settings: Settings = Depends(settings_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> FileResponse:
    return download_document(document_id, repository, settings, current_user)


@router.get("/documents/{document_id}/metadata/")
def document_metadata(
    document_id: int,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    document, _ = _resolve_document(document_id, repository, current_user)
    return {
        "original_checksum": document.checksum_sha256,
        "original_size": document.size_bytes,
        "original_mime_type": document.content_type,
        "media_filename": document.filename,
        "has_archive_version": False,
        "original_metadata": [],
        "archive_checksum": None,
        "archive_media_filename": None,
        "original_filename": document.filename,
        "archive_size": None,
        "archive_metadata": [],
        "lang": None,
    }


@router.get("/documents/{document_id}/suggestions/")
def document_suggestions(
    document_id: int,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    _, llm_result = _resolve_document(document_id, repository, current_user)
    return {
        "correspondents": [_taxonomy_id("correspondent", llm_result.correspondent)] if llm_result else [],
        "tags": [_taxonomy_id("tag", tag) for tag in llm_result.tags] if llm_result else [],
        "document_types": [_taxonomy_id("document_type", llm_result.document_type)] if llm_result else [],
        "storage_paths": [],
        "dates": [llm_result.document_date] if llm_result and llm_result.document_date else [],
    }


@router.get("/documents/{document_id}/notes/")
def list_notes(document_id: int, current_user: User = Depends(_current_user_from_token)) -> list[Any]:
    del document_id, current_user
    return []


@router.post("/documents/{document_id}/notes/")
def add_note(document_id: int, current_user: User = Depends(_current_user_from_token)) -> list[Any]:
    del document_id, current_user
    return []


@router.delete("/documents/{document_id}/notes/")
def delete_note(document_id: int, current_user: User = Depends(_current_user_from_token)) -> list[Any]:
    del document_id, current_user
    return []


@router.get("/documents/{document_id}/share_links/")
def share_links(document_id: int, current_user: User = Depends(_current_user_from_token)) -> list[Any]:
    del document_id, current_user
    return []


@router.get("/documents/{document_id}/logs/")
def document_logs(document_id: int, current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    del document_id, current_user
    return _paginated("/api/documents/logs/", count=0, page=1, page_size=DEFAULT_PAGE_SIZE, results=[])


def _list_labels(
    request_path: str,
    kind: str,
    page: int,
    page_size: int,
    repository: DocumentRepository,
    current_user: User,
) -> dict[str, Any]:
    names = _taxonomy_names(repository, kind)
    stats = _stats_map(repository, current_user, kind)
    rows = [_label_payload(kind, name, stats.get(name, 0), _user_id(current_user)) for name in names]
    start = (page - 1) * page_size
    return _paginated(
        request_path,
        count=len(rows),
        page=page,
        page_size=page_size,
        all_ids=[row["id"] for row in rows],
        results=rows[start : start + page_size],
    )


def _get_label(kind: str, label_id: int, repository: DocumentRepository, current_user: User) -> dict[str, Any]:
    stats = _stats_map(repository, current_user, kind)
    for name in _taxonomy_names(repository, kind):
        if _taxonomy_id(kind, name) == label_id:
            return _label_payload(kind, name, stats.get(name, 0), _user_id(current_user))
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found")


def _create_label(kind: str, payload: dict[str, Any], repository: DocumentRepository, current_user: User) -> dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name is required")
    if kind == "tag":
        repository.add_tags([name])
    elif kind == "correspondent":
        repository.add_correspondent(name)
    elif kind == "document_type":
        repository.add_document_type(name)
    return _label_payload(kind, name, 0, _user_id(current_user))


def _upsert_label(
    kind: str,
    label_id: int,
    payload: dict[str, Any],
    repository: DocumentRepository,
    current_user: User,
) -> dict[str, Any]:
    try:
        current = _get_label(kind, label_id, repository, current_user)
    except HTTPException:
        current = {}
    merged = {"name": current.get("name"), **payload}
    return _create_label(kind, merged, repository, current_user)


@router.get("/tags/")
def list_tags(
    page: int = Query(1, ge=1),
    page_size: int = Query(10_000, ge=1),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    return _list_labels("/api/tags/", "tag", page, page_size, repository, current_user)


@router.post("/tags/", status_code=status.HTTP_201_CREATED)
def create_tag(payload: dict[str, Any], repository: DocumentRepository = Depends(document_repository_dependency), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    return _create_label("tag", payload, repository, current_user)


@router.get("/tags/{label_id}/")
def get_tag(label_id: int, repository: DocumentRepository = Depends(document_repository_dependency), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    return _get_label("tag", label_id, repository, current_user)


@router.patch("/tags/{label_id}/")
def patch_tag(label_id: int, payload: dict[str, Any], repository: DocumentRepository = Depends(document_repository_dependency), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    return _upsert_label("tag", label_id, payload, repository, current_user)


@router.put("/tags/{label_id}/")
def put_tag(label_id: int, payload: dict[str, Any], repository: DocumentRepository = Depends(document_repository_dependency), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    return _upsert_label("tag", label_id, payload, repository, current_user)


@router.delete("/tags/{label_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(label_id: int, current_user: User = Depends(_current_user_from_token)) -> None:
    del label_id, current_user


@router.get("/correspondents/")
def list_correspondents(
    page: int = Query(1, ge=1),
    page_size: int = Query(10_000, ge=1),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    return _list_labels("/api/correspondents/", "correspondent", page, page_size, repository, current_user)


@router.post("/correspondents/", status_code=status.HTTP_201_CREATED)
def create_correspondent(payload: dict[str, Any], repository: DocumentRepository = Depends(document_repository_dependency), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    return _create_label("correspondent", payload, repository, current_user)


@router.get("/correspondents/{label_id}/")
def get_correspondent(label_id: int, repository: DocumentRepository = Depends(document_repository_dependency), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    return _get_label("correspondent", label_id, repository, current_user)


@router.patch("/correspondents/{label_id}/")
def patch_correspondent(label_id: int, payload: dict[str, Any], repository: DocumentRepository = Depends(document_repository_dependency), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    return _upsert_label("correspondent", label_id, payload, repository, current_user)


@router.put("/correspondents/{label_id}/")
def put_correspondent(label_id: int, payload: dict[str, Any], repository: DocumentRepository = Depends(document_repository_dependency), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    return _upsert_label("correspondent", label_id, payload, repository, current_user)


@router.delete("/correspondents/{label_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_correspondent(label_id: int, current_user: User = Depends(_current_user_from_token)) -> None:
    del label_id, current_user


@router.get("/document_types/")
def list_document_types(
    page: int = Query(1, ge=1),
    page_size: int = Query(10_000, ge=1),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    return _list_labels("/api/document_types/", "document_type", page, page_size, repository, current_user)


@router.post("/document_types/", status_code=status.HTTP_201_CREATED)
def create_document_type(payload: dict[str, Any], repository: DocumentRepository = Depends(document_repository_dependency), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    return _create_label("document_type", payload, repository, current_user)


@router.get("/document_types/{label_id}/")
def get_document_type(label_id: int, repository: DocumentRepository = Depends(document_repository_dependency), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    return _get_label("document_type", label_id, repository, current_user)


@router.patch("/document_types/{label_id}/")
def patch_document_type(label_id: int, payload: dict[str, Any], repository: DocumentRepository = Depends(document_repository_dependency), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    return _upsert_label("document_type", label_id, payload, repository, current_user)


@router.put("/document_types/{label_id}/")
def put_document_type(label_id: int, payload: dict[str, Any], repository: DocumentRepository = Depends(document_repository_dependency), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    return _upsert_label("document_type", label_id, payload, repository, current_user)


@router.delete("/document_types/{label_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_type(label_id: int, current_user: User = Depends(_current_user_from_token)) -> None:
    del label_id, current_user


@router.get("/storage_paths/")
def list_storage_paths(page: int = Query(1, ge=1), page_size: int = Query(10_000, ge=1), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    del current_user
    return _paginated("/api/storage_paths/", count=0, page=page, page_size=page_size, all_ids=[], results=[])


@router.get("/custom_fields/")
def list_custom_fields(page: int = Query(1, ge=1), page_size: int = Query(10_000, ge=1), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    del current_user
    return _paginated("/api/custom_fields/", count=0, page=page, page_size=page_size, all_ids=[], results=[])


@router.get("/saved_views/")
def list_saved_views(page: int = Query(1, ge=1), page_size: int = Query(10_000, ge=1), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    del current_user
    return _paginated("/api/saved_views/", count=0, page=page, page_size=page_size, all_ids=[], results=[])


@router.get("/tasks/")
def list_tasks(page: int = Query(1, ge=1), page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1), current_user: User = Depends(_current_user_from_token)) -> dict[str, Any]:
    del current_user
    return _paginated("/api/tasks/", count=0, page=page, page_size=page_size, results=[])


@router.get("/tasks/{task_id}")
def get_task(task_id: int, current_user: User = Depends(_current_user_from_token)) -> None:
    del task_id, current_user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")


@router.post("/acknowledge_tasks/")
def acknowledge_tasks(payload: dict[str, Any], current_user: User = Depends(_current_user_from_token)) -> dict[str, int]:
    del current_user
    tasks = payload.get("tasks", []) if isinstance(payload, dict) else []
    return {"result": len(tasks)}


@router.get("/search/autocomplete/")
def search_autocomplete(
    term: str = Query(""),
    limit: int = Query(10, ge=1),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> list[str]:
    values: list[str] = []
    for document, llm_result in _owner_rows(repository, current_user):
        values.append(_document_title(document, llm_result))
        if llm_result is not None:
            values.extend([llm_result.correspondent, llm_result.document_type, *llm_result.tags])
    needle = term.casefold()
    unique = []
    seen = set()
    for value in values:
        if needle in value.casefold() and value.casefold() not in seen:
            seen.add(value.casefold())
            unique.append(value)
        if len(unique) >= limit:
            break
    return unique


@router.get("/search/")
def search(
    query: str = Query(""),
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(_current_user_from_token),
) -> dict[str, Any]:
    rows = [
        (document, llm_result)
        for document, llm_result in _owner_rows(repository, current_user)
        if _matches_query(document, llm_result, query, repository)
    ]
    return {
        "total": len(rows),
        "documents": [_document_payload(document, llm_result, repository, include_content=False) for document, llm_result in rows[:25]],
        "saved_views": [],
        "tags": [],
        "correspondents": [],
        "document_types": [],
        "storage_paths": [],
        "users": [],
        "groups": [],
        "mail_rules": [],
        "mail_accounts": [],
        "workflows": [],
        "custom_fields": [],
    }
