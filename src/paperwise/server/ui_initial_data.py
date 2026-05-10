from paperwise.application.interfaces import DocumentRepository
from paperwise.application.services.activity import owner_activity_summary
from paperwise.application.services.chat_threads import migrate_legacy_chat_threads
from paperwise.application.services.document_listing import list_filtered_documents
from paperwise.application.services.llm_preferences import (
    llm_provider_defaults_payload,
    llm_supported_providers_payload,
    ocr_llm_provider_defaults_payload,
    ocr_supported_providers_payload,
)
from paperwise.application.services.pending_documents import (
    PENDING_DOCUMENT_STATUSES,
    list_pending_documents,
)
from paperwise.application.services.user_preferences import load_normalized_user_preferences
from paperwise.domain.models import User
from paperwise.server.document_access import get_owned_document_or_404
from paperwise.server.ui_page import DEFAULT_UI_THEME, SUPPORTED_UI_THEMES
from paperwise.server.ui_payloads import document_list_item, history_event_item
from paperwise.server.ui_fragments import chat_thread_list_html


def page_initial_data(
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


def tag_stats(repository: DocumentRepository, current_user: User) -> list[dict]:
    return [
        {"tag": tag, "document_count": count}
        for tag, count in repository.list_owner_tag_stats(current_user.id)
    ]


def tag_stats_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = page_initial_data(current_user, repository)
    if current_user is None:
        return {**initial_data, "tag_stats": []}
    return {**initial_data, "tag_stats": tag_stats(repository, current_user)}


def document_type_stats(repository: DocumentRepository, current_user: User) -> list[dict]:
    return [
        {"document_type": document_type, "document_count": count}
        for document_type, count in repository.list_owner_document_type_stats(current_user.id)
    ]


def document_type_stats_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = page_initial_data(current_user, repository)
    if current_user is None:
        return {**initial_data, "document_type_stats": []}
    return {
        **initial_data,
        "document_type_stats": document_type_stats(repository, current_user),
    }


def activity_data(repository: DocumentRepository, current_user: User, *, limit: int) -> dict:
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


def activity_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = page_initial_data(current_user, repository)
    if current_user is None:
        return {**initial_data, "activity_documents": [], "activity_total_tokens": 0}
    return {
        **initial_data,
        **activity_data(repository, current_user, limit=20),
    }


def activity_partial_data(
    repository: DocumentRepository,
    current_user: User,
    *,
    limit: int = 20,
) -> dict:
    normalized_limit = min(100, max(1, int(limit or 20)))
    return activity_data(repository, current_user, limit=normalized_limit)


def document_filter_options(repository: DocumentRepository, current_user: User) -> dict:
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


def documents_initial_data(
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
    data = page_initial_data(current_user, repository)
    normalized_page_size = max(1, min(100, int(page_size or 20)))
    requested_page = max(1, int(page or 1))
    if current_user is None:
        data.update(
            {
                "documents": [],
                "documents_page": requested_page,
                "documents_page_size": normalized_page_size,
                "documents_total": 0,
                "documents_processing_count": 0,
            }
        )
        if include_filter_options:
            data["document_filter_options"] = {
                "tags": [],
                "correspondents": [],
                "document_types": [],
                "statuses": ["received", "processing", "failed", "ready"],
            }
        return data
    requested_offset = (requested_page - 1) * normalized_page_size
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
    current_page = requested_page
    if requested_offset >= listing.total and listing.total > 0:
        current_page = max(1, ((listing.total - 1) // normalized_page_size) + 1)
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
            offset=(current_page - 1) * normalized_page_size,
        )
    processing_count = repository.count_owner_documents_by_statuses(
        owner_id=current_user.id,
        statuses=PENDING_DOCUMENT_STATUSES,
    )
    data.update(
        {
            "documents": [
                document_list_item(document, llm_result)
                for document, llm_result in listing.rows
            ],
            "documents_page": current_page,
            "documents_page_size": normalized_page_size,
            "documents_total": listing.total,
            "documents_processing_count": processing_count,
        }
    )
    if include_filter_options:
        data["document_filter_options"] = document_filter_options(repository, current_user)
    return data


def pending_documents(repository: DocumentRepository, current_user: User) -> list[dict]:
    return [
        document_list_item(document, llm_result)
        for document, llm_result in list_pending_documents(
            repository=repository,
            owner_id=current_user.id,
            limit=200,
        )
    ]


def pending_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    initial_data = page_initial_data(current_user, repository)
    if current_user is None:
        return {**initial_data, "pending_documents": []}
    return {
        **initial_data,
        "pending_documents": pending_documents(repository, current_user),
    }


def document_detail_initial_data(
    repository: DocumentRepository,
    current_user: User | None,
    document_id: str | None,
) -> dict:
    initial_data = page_initial_data(current_user, repository)
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


def chat_thread_initial_data(repository: DocumentRepository, current_user: User | None) -> dict:
    if current_user is None:
        return {**page_initial_data(current_user, repository), "chat_threads": []}
    migrate_legacy_chat_threads(repository, current_user)
    return {
        **page_initial_data(current_user, repository),
        "chat_threads": [
            {
                "id": thread.id,
                "title": thread.title or "Untitled chat",
                "message_count": len(thread.messages),
                "created_at": thread.created_at.isoformat(),
                "updated_at": thread.updated_at.isoformat(),
            }
            for thread in repository.list_chat_threads(current_user.id, 20)
        ],
    }


def chat_threads_partial_data(
    repository: DocumentRepository,
    current_user: User,
    *,
    active_thread_id: str = "",
    query: str = "",
) -> dict:
    data = chat_thread_initial_data(repository, current_user)
    threads = data["chat_threads"]
    return {
        "chat_threads": threads,
        "thread_list_html": chat_thread_list_html(
            threads,
            active_thread_id=active_thread_id,
            query=query,
        ),
    }
