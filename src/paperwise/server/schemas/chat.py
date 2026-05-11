from typing import Any

from pydantic import BaseModel, Field


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


class ChatThreadResponse(ChatThreadSummaryResponse):
    messages: list[dict[str, Any]]
    token_usage: ChatTokenUsageResponse = Field(default_factory=ChatTokenUsageResponse)
