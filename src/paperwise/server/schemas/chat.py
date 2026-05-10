from typing import Any

from pydantic import BaseModel, Field

from paperwise.domain.models import ChatThread


class ChatMessageRequest(BaseModel):
    role: str = Field(min_length=1, max_length=20)
    content: str = Field(default="", max_length=12000)


class ChatScopeRequest(BaseModel):
    tag: list[str] = Field(default_factory=list)
    document_type: list[str] = Field(default_factory=list)
    correspondent: list[str] = Field(default_factory=list)
    date_from: str | None = None
    date_to: str | None = None


class ChatRequest(BaseModel):
    thread_id: str | None = Field(default=None, max_length=64)
    messages: list[ChatMessageRequest] = Field(min_length=1, max_length=30)
    scope: ChatScopeRequest = Field(default_factory=ChatScopeRequest)
    top_k_chunks: int = Field(default=18, ge=3, le=60)
    max_documents: int = Field(default=12, ge=1, le=50)
    debug: bool = False


class ChatCitationResponse(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    quote: str


class ChatToolCallResponse(BaseModel):
    name: str
    arguments: dict[str, Any]
    result_count: int


class ChatTokenUsageResponse(BaseModel):
    total_tokens: int = 0
    llm_requests: int = 0


class ChatResponse(BaseModel):
    thread_id: str | None = None
    message: ChatMessageRequest
    citations: list[ChatCitationResponse]
    tool_calls: list[ChatToolCallResponse]
    token_usage: ChatTokenUsageResponse = Field(default_factory=ChatTokenUsageResponse)
    debug: dict[str, Any] | None = None


class ChatThreadSummaryResponse(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str

    @classmethod
    def from_domain(cls, thread: ChatThread) -> "ChatThreadSummaryResponse":
        return cls(
            id=thread.id,
            title=thread.title or "Untitled chat",
            message_count=len(thread.messages),
            created_at=thread.created_at.isoformat(),
            updated_at=thread.updated_at.isoformat(),
        )


class ChatThreadResponse(ChatThreadSummaryResponse):
    messages: list[dict[str, Any]]
    token_usage: ChatTokenUsageResponse = Field(default_factory=ChatTokenUsageResponse)

    @classmethod
    def from_domain(cls, thread: ChatThread) -> "ChatThreadResponse":
        usage = dict(thread.token_usage or {})
        return cls(
            **ChatThreadSummaryResponse.from_domain(thread).model_dump(mode="json"),
            messages=[dict(message) for message in thread.messages],
            token_usage=ChatTokenUsageResponse(
                total_tokens=int(usage.get("total_tokens") or 0),
                llm_requests=int(usage.get("llm_requests") or 0),
            ),
        )
