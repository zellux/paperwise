from datetime import UTC, datetime
from typing import Any
from typing import Protocol

from paperwise.application.interfaces import ChatThreadRepository, PreferenceRepository
from paperwise.domain.models import ChatThread, User, UserPreference

CHAT_THREADS_PREFERENCE_KEY = "chat_threads"
MAX_STORED_CHAT_MESSAGES = 40


class LegacyChatThreadRepository(PreferenceRepository, ChatThreadRepository, Protocol):
    pass


def thread_title_from_messages(messages: list[dict[str, Any]]) -> str:
    for message in messages:
        if message.get("role") != "user":
            continue
        content = " ".join(str(message.get("content") or "").split())
        if content:
            return content[:80]
    return "New chat"


def migrate_legacy_chat_threads(repository: LegacyChatThreadRepository, current_user: User) -> None:
    preference = repository.get_user_preference(current_user.id)
    preferences = dict(preference.preferences) if preference is not None else {}
    legacy_threads = _chat_threads_from_preferences(preferences)
    if not legacy_threads:
        return
    for legacy_thread in legacy_threads:
        thread = _legacy_chat_thread_to_model(current_user, legacy_thread)
        if thread is None:
            continue
        if repository.get_chat_thread(current_user.id, thread.id) is None:
            repository.save_chat_thread(thread)
    preferences.pop(CHAT_THREADS_PREFERENCE_KEY, None)
    repository.save_user_preference(UserPreference(user_id=current_user.id, preferences=preferences))


def _parse_chat_datetime(value: Any, *, fallback: datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return fallback
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return fallback
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _chat_threads_from_preferences(preferences: dict[str, Any]) -> list[dict[str, Any]]:
    raw_threads = preferences.get(CHAT_THREADS_PREFERENCE_KEY, [])
    if not isinstance(raw_threads, list):
        return []
    threads = [thread for thread in raw_threads if isinstance(thread, dict) and str(thread.get("id") or "").strip()]
    return sorted(
        threads,
        key=lambda item: str(item.get("updated_at") or item.get("created_at") or ""),
        reverse=True,
    )


def _legacy_chat_thread_to_model(current_user: User, thread: dict[str, Any]) -> ChatThread | None:
    thread_id = str(thread.get("id") or "").strip()
    if not thread_id:
        return None
    raw_messages = thread.get("messages", [])
    messages = [dict(message) for message in raw_messages if isinstance(message, dict)] if isinstance(raw_messages, list) else []
    raw_usage = thread.get("token_usage", {})
    token_usage = dict(raw_usage) if isinstance(raw_usage, dict) else {}
    now = datetime.now(UTC)
    created_at = _parse_chat_datetime(thread.get("created_at"), fallback=now)
    updated_at = _parse_chat_datetime(thread.get("updated_at"), fallback=created_at)
    title = str(thread.get("title") or "").strip() or thread_title_from_messages(messages)
    return ChatThread(
        id=thread_id,
        owner_id=current_user.id,
        title=title[:256] or "Untitled chat",
        messages=messages[-MAX_STORED_CHAT_MESSAGES:],
        token_usage=token_usage,
        created_at=created_at,
        updated_at=updated_at,
    )
