import json
from typing import Any, Protocol

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse

from paperwise.application.interfaces import ChatThreadRepository, LLMProvider
from paperwise.application.services.chat_runtime import (
    ChatRuntimeEvent,
    ChatRuntimeResult,
    ChatRuntimeUnsupportedError,
    iter_chat_runtime_events,
    run_chat_runtime,
)
from paperwise.application.services.chat_tools import ChatToolRepository, ChatToolScope
from paperwise.application.services.grounded_qa import is_timeout_error
from paperwise.application.services.chat_threads import (
    migrate_legacy_chat_threads,
    save_chat_thread_turn,
)
from paperwise.application.services.llm_preferences import LLM_TASK_GROUNDED_QA
from paperwise.domain.models import User
from paperwise.server.schemas.chat import (
    ChatCitationResponse,
    ChatMessageRequest,
    ChatRequest,
    ChatResponse,
    ChatScopeRequest,
    ChatThreadResponse,
    ChatThreadSummaryResponse,
    ChatTokenUsageResponse,
    ChatToolCallResponse,
)
from paperwise.server.presenters.chat import (
    present_chat_thread,
    present_chat_thread_summary,
)
from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    llm_provider_dependency,
)
from paperwise.server.http_llm_provider import resolve_http_llm_provider_for_user

router = APIRouter(prefix="/query", tags=["query"])


CHAT_SYSTEM_PROMPT = (
    "You are Paperwise's conversational document assistant. Use the available tools to inspect the user's "
    "documents, tags, metadata, and grounded text chunks. Do not answer from outside knowledge. For document "
    "content claims, cite returned source titles or chunk IDs in your Markdown answer. Always query across all "
    "owner-visible documents unless a metadata filter is needed. If the tools return no useful evidence, say "
    "that the documents do not contain enough evidence. Prefer metadata tools for "
    "questions about counts, available tags, document types, dates, correspondents, or document lists."
)
MAX_CHAT_TOOL_ROUNDS = 3
MAX_CHAT_THREADS = 20


class ChatQueryRepository(ChatThreadRepository, ChatToolRepository, Protocol):
    pass


CHAT_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_document_chunks",
            "description": "Search OCR text chunks in owner-visible documents using optional metadata filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "document_types": {"type": "array", "items": {"type": "string"}},
                    "correspondents": {"type": "array", "items": {"type": "string"}},
                    "date_from": {"type": "string", "description": "Inclusive YYYY-MM-DD lower bound."},
                    "date_to": {"type": "string", "description": "Inclusive YYYY-MM-DD upper bound."},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 60},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_document_metadata",
            "description": "List documents by title, tag, type, correspondent, or document date without reading full text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title_query": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "document_types": {"type": "array", "items": {"type": "string"}},
                    "correspondents": {"type": "array", "items": {"type": "string"}},
                    "date_from": {"type": "string"},
                    "date_to": {"type": "string"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_taxonomy",
            "description": "Return available tags, document types, and correspondents for all owner-visible documents.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_document_context",
            "description": "Fetch OCR chunks and metadata for one owner-visible document by document_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string"},
                    "max_chunks": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                "required": ["document_id"],
            },
        },
    },
]


def _save_chat_thread(
    *,
    repository: ChatThreadRepository,
    current_user: User,
    payload: ChatRequest,
    response: ChatResponse,
) -> ChatResponse:
    assistant_message: dict[str, Any] = {"content": response.message.content}
    if response.citations:
        assistant_message["citations"] = [
            citation.model_dump(mode="json") for citation in response.citations
        ]
    response.thread_id = save_chat_thread_turn(
        repository=repository,
        current_user=current_user,
        thread_id=payload.thread_id,
        request_messages=[message.model_dump(mode="json") for message in payload.messages],
        assistant_message=assistant_message,
        token_usage=response.token_usage.model_dump(mode="json"),
    )
    return response


@router.get("/chat/threads", response_model=list[ChatThreadSummaryResponse])
def list_chat_threads_endpoint(
    repository: ChatThreadRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[ChatThreadSummaryResponse]:
    migrate_legacy_chat_threads(repository, current_user)
    return [
        present_chat_thread_summary(thread)
        for thread in repository.list_chat_threads(current_user.id, MAX_CHAT_THREADS)
    ]


@router.get("/chat/threads/{thread_id}", response_model=ChatThreadResponse)
def get_chat_thread_endpoint(
    thread_id: str,
    repository: ChatThreadRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> ChatThreadResponse:
    migrate_legacy_chat_threads(repository, current_user)
    thread = repository.get_chat_thread(current_user.id, thread_id)
    if thread is not None:
        return present_chat_thread(thread)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat thread not found.")


@router.delete("/chat/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_thread_endpoint(
    thread_id: str,
    repository: ChatThreadRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> Response:
    migrate_legacy_chat_threads(repository, current_user)
    if not repository.delete_chat_thread(current_user.id, thread_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat thread not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _extract_tool_citations(tool_payloads: list[dict[str, Any]]) -> list[ChatCitationResponse]:
    citations: list[ChatCitationResponse] = []
    seen: set[str] = set()
    for payload in tool_payloads:
        candidates = list(payload.get("results", []))
        candidates.extend(payload.get("chunks", []))
        for item in candidates:
            chunk_id = str(item.get("chunk_id") or "").strip()
            document_id = str(item.get("document_id") or "").strip()
            if not chunk_id or not document_id or chunk_id in seen:
                continue
            seen.add(chunk_id)
            citations.append(
                ChatCitationResponse(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    title=str(item.get("title") or ""),
                    quote=str(item.get("content") or "")[:240],
                )
            )
    return citations[:20]


def _build_chat_messages(payload: ChatRequest) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    for item in payload.messages:
        role = item.role.strip().lower()
        if role not in {"user", "assistant"}:
            continue
        content = item.content.strip()
        if not content:
            continue
        messages.append({"role": role, "content": content})
    if len(messages) == 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one user message is required.")
    return messages


def _chat_tool_scope(scope: ChatScopeRequest) -> ChatToolScope:
    return ChatToolScope(
        tag=list(scope.tag or []),
        document_type=list(scope.document_type or []),
        correspondent=list(scope.correspondent or []),
        date_from=scope.date_from,
        date_to=scope.date_to,
    )


def _chat_response_from_runtime_result(
    *,
    payload: ChatRequest,
    result: ChatRuntimeResult,
) -> ChatResponse:
    return ChatResponse(
        message=ChatMessageRequest(role="assistant", content=result.content),
        citations=_extract_tool_citations(result.tool_payloads),
        tool_calls=[ChatToolCallResponse(**tool_call) for tool_call in result.tool_calls],
        token_usage=ChatTokenUsageResponse(**result.token_usage),
        debug={"steps": result.debug_steps} if payload.debug else None,
    )


def _raise_chat_runtime_http_exception(exc: Exception) -> None:
    if isinstance(exc, ChatRuntimeUnsupportedError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if is_timeout_error(exc):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(
                "The LLM request timed out before completion. "
                "Please retry, reduce scope, or lower context limits in Settings."
            ),
        ) from exc
    if isinstance(exc, RuntimeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise exc


def _chat_with_tools(
    *,
    repository: ChatQueryRepository,
    llm_provider: LLMProvider,
    current_user: User,
    payload: ChatRequest,
) -> ChatResponse:
    messages = _build_chat_messages(payload)
    try:
        runtime_result = run_chat_runtime(
            repository=repository,
            llm_provider=llm_provider,
            current_user=current_user,
            messages=messages,
            tools=CHAT_TOOLS,
            scope=_chat_tool_scope(payload.scope),
            top_k_chunks=payload.top_k_chunks,
            max_documents=payload.max_documents,
            max_tool_rounds=MAX_CHAT_TOOL_ROUNDS,
        )
    except Exception as exc:
        _raise_chat_runtime_http_exception(exc)
    response = _chat_response_from_runtime_result(payload=payload, result=runtime_result)
    return _save_chat_thread(
        repository=repository,
        current_user=current_user,
        payload=payload,
        response=response,
    )


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _chat_sse_event_from_runtime_event(event: ChatRuntimeEvent) -> str:
    if event.type == "final":
        raise ValueError("Final chat runtime events need response assembly before SSE serialization.")
    if not isinstance(event.data, dict):
        raise ValueError(f"Unexpected data for chat runtime event {event.type}.")
    return _sse_event(event.type, event.data)


def _iter_chat_events(
    *,
    repository: ChatQueryRepository,
    llm_provider: LLMProvider,
    current_user: User,
    payload: ChatRequest,
):
    try:
        messages = _build_chat_messages(payload)
        for event in iter_chat_runtime_events(
            repository=repository,
            llm_provider=llm_provider,
            current_user=current_user,
            messages=messages,
            tools=CHAT_TOOLS,
            scope=_chat_tool_scope(payload.scope),
            top_k_chunks=payload.top_k_chunks,
            max_documents=payload.max_documents,
            max_tool_rounds=MAX_CHAT_TOOL_ROUNDS,
        ):
            if event.type != "final":
                yield _chat_sse_event_from_runtime_event(event)
                continue
            if not isinstance(event.data, ChatRuntimeResult):
                raise RuntimeError("Chat runtime returned an invalid final event.")
            response = _chat_response_from_runtime_result(payload=payload, result=event.data)
            response = _save_chat_thread(
                repository=repository,
                current_user=current_user,
                payload=payload,
                response=response,
            )
            yield _sse_event("final", response.model_dump(mode="json"))
    except Exception as exc:
        if is_timeout_error(exc):
            detail = (
                "The LLM request timed out before completion. "
                "Please retry, reduce scope, or lower context limits in Settings."
            )
        elif isinstance(exc, HTTPException):
            detail = str(exc.detail)
        else:
            detail = str(exc)
        yield _sse_event("error", {"detail": detail})


@router.post("/chat", response_model=ChatResponse)
def chat_all_documents_endpoint(
    payload: ChatRequest,
    repository: ChatQueryRepository = Depends(document_repository_dependency),
    provider_override: LLMProvider | None = Depends(llm_provider_dependency),
    current_user: User = Depends(current_user_dependency),
) -> ChatResponse:
    llm_provider = resolve_http_llm_provider_for_user(
        repository=repository,
        user_id=current_user.id,
        provider_override=provider_override,
        task=LLM_TASK_GROUNDED_QA,
        missing_provider_detail="Configure a Grounded Q&A LLM connection in Settings before chatting with your documents.",
        missing_api_key_detail="Selected Grounded Q&A LLM connection requires an API key in Settings.",
        missing_base_url_detail="Custom Grounded Q&A connection requires a base URL in Settings.",
    )
    return _chat_with_tools(
        repository=repository,
        llm_provider=llm_provider,
        current_user=current_user,
        payload=payload,
    )


@router.post("/chat/stream")
def stream_chat_all_documents_endpoint(
    payload: ChatRequest,
    repository: ChatQueryRepository = Depends(document_repository_dependency),
    provider_override: LLMProvider | None = Depends(llm_provider_dependency),
    current_user: User = Depends(current_user_dependency),
) -> StreamingResponse:
    llm_provider = resolve_http_llm_provider_for_user(
        repository=repository,
        user_id=current_user.id,
        provider_override=provider_override,
        task=LLM_TASK_GROUNDED_QA,
        missing_provider_detail="Configure a Grounded Q&A LLM connection in Settings before chatting with your documents.",
        missing_api_key_detail="Selected Grounded Q&A LLM connection requires an API key in Settings.",
        missing_base_url_detail="Custom Grounded Q&A connection requires a base URL in Settings.",
    )
    return StreamingResponse(
        _iter_chat_events(
            repository=repository,
            llm_provider=llm_provider,
            current_user=current_user,
            payload=payload,
        ),
        media_type="text/event-stream",
    )
