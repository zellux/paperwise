from typing import Any

from paperwise.domain.models import ChatThread
from paperwise.server.schemas.chat import (
    ChatThreadResponse,
    ChatThreadSummaryResponse,
    ChatTokenUsageResponse,
)


def present_chat_thread_summary(thread: ChatThread) -> ChatThreadSummaryResponse:
    return ChatThreadSummaryResponse(
        id=thread.id,
        title=thread.title or "Untitled chat",
        message_count=len(thread.messages),
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
    )


def present_chat_thread(thread: ChatThread) -> ChatThreadResponse:
    usage: dict[str, Any] = dict(thread.token_usage or {})
    return ChatThreadResponse(
        **present_chat_thread_summary(thread).model_dump(mode="json"),
        messages=[dict(message) for message in thread.messages],
        token_usage=ChatTokenUsageResponse(
            total_tokens=int(usage.get("total_tokens") or 0),
            llm_requests=int(usage.get("llm_requests") or 0),
        ),
    )
