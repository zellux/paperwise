import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse

from paperwise.application.interfaces import DocumentRepository, LLMProvider
from paperwise.application.services.chat_tools import ChatToolScope, execute_chat_tool
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
from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    llm_provider_dependency,
)
from paperwise.server.llm_provider import resolve_http_llm_provider_for_user

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
    repository: DocumentRepository,
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
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[ChatThreadSummaryResponse]:
    migrate_legacy_chat_threads(repository, current_user)
    return [
        ChatThreadSummaryResponse.from_domain(thread)
        for thread in repository.list_chat_threads(current_user.id, MAX_CHAT_THREADS)
    ]


@router.get("/chat/threads/{thread_id}", response_model=ChatThreadResponse)
def get_chat_thread_endpoint(
    thread_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> ChatThreadResponse:
    migrate_legacy_chat_threads(repository, current_user)
    thread = repository.get_chat_thread(current_user.id, thread_id)
    if thread is not None:
        return ChatThreadResponse.from_domain(thread)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat thread not found.")


@router.delete("/chat/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_thread_endpoint(
    thread_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
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


def _record_chat_token_usage(token_usage: dict[str, int], response: dict[str, Any]) -> None:
    total_tokens = response.get("llm_total_tokens") if isinstance(response, dict) else None
    if not isinstance(total_tokens, int) or total_tokens <= 0:
        return
    token_usage["total_tokens"] = token_usage.get("total_tokens", 0) + total_tokens
    token_usage["llm_requests"] = token_usage.get("llm_requests", 0) + 1


def _parse_chat_tool_call(call: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    call_id = str(call.get("id") or uuid4())
    name = str(call.get("name") or "").strip()
    raw_arguments = call.get("arguments", "{}")
    try:
        arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else dict(raw_arguments or {})
    except (TypeError, ValueError):
        arguments = {}
    return call_id, name, arguments


def _append_chat_tool_messages(
    *,
    messages: list[dict[str, Any]],
    last_response: dict[str, Any],
    assistant_tool_calls: list[dict[str, Any]],
    tool_results: list[tuple[str, str, dict[str, Any]]],
) -> None:
    messages.append(
        {
            "role": "assistant",
            "content": str(last_response.get("content") or ""),
            "tool_calls": assistant_tool_calls,
        }
    )
    for call_id, name, result in tool_results:
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call_id,
                "name": name,
                "content": json.dumps(result),
            }
        )


def _chat_with_tools(
    *,
    repository: DocumentRepository,
    llm_provider: LLMProvider,
    current_user: User,
    payload: ChatRequest,
) -> ChatResponse:
    answer_with_tools = getattr(llm_provider, "answer_with_tools", None)
    if not callable(answer_with_tools):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected Grounded Q&A provider does not support conversational tool use.",
        )
    messages = _build_chat_messages(payload)
    tool_calls_for_response: list[ChatToolCallResponse] = []
    tool_payloads: list[dict[str, Any]] = []
    debug_steps: list[dict[str, Any]] = []
    token_usage: dict[str, int] = {"total_tokens": 0, "llm_requests": 0}
    last_response: dict[str, Any] = {}
    exhausted_tool_rounds = False
    tool_scope = _chat_tool_scope(payload.scope)
    for _ in range(MAX_CHAT_TOOL_ROUNDS):
        try:
            last_response = answer_with_tools(messages=messages, tools=CHAT_TOOLS)
            _record_chat_token_usage(token_usage, last_response)
        except Exception as exc:
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
            raise
        tool_calls = last_response.get("tool_calls", []) if isinstance(last_response, dict) else []
        if not tool_calls:
            break
        assistant_tool_calls: list[dict[str, Any]] = []
        tool_results: list[tuple[str, str, dict[str, Any]]] = []
        for call in tool_calls:
            call_id, name, arguments = _parse_chat_tool_call(call)
            assistant_tool_calls.append(
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(arguments)},
                }
            )
            result = execute_chat_tool(
                repository=repository,
                llm_provider=llm_provider,
                current_user=current_user,
                scope=tool_scope,
                top_k_chunks=payload.top_k_chunks,
                max_documents=payload.max_documents,
                name=name,
                arguments=arguments,
            )
            tool_payloads.append(result)
            tool_results.append((call_id, name, result))
            result_count = int(result.get("total_results") or result.get("returned_results") or 0)
            tool_calls_for_response.append(
                ChatToolCallResponse(name=name, arguments=arguments, result_count=result_count)
            )
            debug_steps.append({"tool": name, "arguments": arguments, "result": result})
        _append_chat_tool_messages(
            messages=messages,
            last_response=last_response,
            assistant_tool_calls=assistant_tool_calls,
            tool_results=tool_results,
        )
        if len(tool_calls_for_response) >= 8:
            exhausted_tool_rounds = True
            break
    else:
        exhausted_tool_rounds = True
    if exhausted_tool_rounds:
        messages.append(
            {
                "role": "user",
                "content": (
                    "Use the tool results already provided and write the final answer now. "
                    "Do not request more tools."
                ),
            }
        )
        try:
            last_response = answer_with_tools(messages=messages, tools=[])
            _record_chat_token_usage(token_usage, last_response)
        except Exception as exc:
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
            raise
    content = str(last_response.get("content") or "").strip()
    if not content:
        content = "I could not find enough evidence in the documents."
    response = ChatResponse(
        message=ChatMessageRequest(role="assistant", content=content),
        citations=_extract_tool_citations(tool_payloads),
        tool_calls=tool_calls_for_response,
        token_usage=ChatTokenUsageResponse(**token_usage),
        debug={"steps": debug_steps} if payload.debug else None,
    )
    return _save_chat_thread(
        repository=repository,
        current_user=current_user,
        payload=payload,
        response=response,
    )


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _iter_chat_events(
    *,
    repository: DocumentRepository,
    llm_provider: LLMProvider,
    current_user: User,
    payload: ChatRequest,
):
    answer_with_tools = getattr(llm_provider, "answer_with_tools", None)
    if not callable(answer_with_tools):
        yield _sse_event(
            "error",
            {"detail": "Selected Grounded Q&A provider does not support conversational tool use."},
        )
        return

    try:
        messages = _build_chat_messages(payload)
    except HTTPException as exc:
        yield _sse_event("error", {"detail": str(exc.detail)})
        return

    tool_calls_for_response: list[ChatToolCallResponse] = []
    tool_payloads: list[dict[str, Any]] = []
    debug_steps: list[dict[str, Any]] = []
    token_usage: dict[str, int] = {"total_tokens": 0, "llm_requests": 0}
    last_response: dict[str, Any] = {}
    exhausted_tool_rounds = False
    tool_scope = _chat_tool_scope(payload.scope)
    try:
        for round_index in range(MAX_CHAT_TOOL_ROUNDS):
            if tool_calls_for_response:
                status_detail = (
                    f"Reading {len(tool_calls_for_response)} tool result(s) and writing an answer, "
                    f"round {round_index + 1}."
                )
            else:
                status_detail = f"Choosing document tools, round {round_index + 1}."
            yield _sse_event(
                "status",
                {"label": "LLM request", "detail": status_detail},
            )
            last_response = answer_with_tools(messages=messages, tools=CHAT_TOOLS)
            _record_chat_token_usage(token_usage, last_response)
            tool_calls = last_response.get("tool_calls", []) if isinstance(last_response, dict) else []
            yield _sse_event(
                "llm_response",
                {
                    "label": "LLM response",
                    "tool_call_count": len(tool_calls),
                    "token_usage": token_usage,
                },
            )
            yield _sse_event("token_usage", token_usage)
            if not tool_calls:
                break

            assistant_tool_calls: list[dict[str, Any]] = []
            tool_results: list[tuple[str, str, dict[str, Any]]] = []
            for call in tool_calls:
                call_id, name, arguments = _parse_chat_tool_call(call)
                assistant_tool_calls.append(
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(arguments)},
                    }
                )
                yield _sse_event("tool_call", {"name": name, "arguments": arguments})
                result = execute_chat_tool(
                    repository=repository,
                    llm_provider=llm_provider,
                    current_user=current_user,
                    scope=tool_scope,
                    top_k_chunks=payload.top_k_chunks,
                    max_documents=payload.max_documents,
                    name=name,
                    arguments=arguments,
                )
                tool_payloads.append(result)
                tool_results.append((call_id, name, result))
                result_count = int(result.get("total_results") or result.get("returned_results") or 0)
                tool_calls_for_response.append(
                    ChatToolCallResponse(name=name, arguments=arguments, result_count=result_count)
                )
                debug_steps.append({"tool": name, "arguments": arguments, "result": result})
                yield _sse_event("tool_result", {"name": name, "result_count": result_count})

            _append_chat_tool_messages(
                messages=messages,
                last_response=last_response,
                assistant_tool_calls=assistant_tool_calls,
                tool_results=tool_results,
            )
            if len(tool_calls_for_response) >= 8:
                exhausted_tool_rounds = True
                break
        else:
            exhausted_tool_rounds = True

        if exhausted_tool_rounds:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Use the tool results already provided and write the final answer now. "
                        "Do not request more tools."
                    ),
                }
            )
            yield _sse_event(
                "status",
                {"label": "LLM request", "detail": "Writing final answer from collected tool results."},
            )
            last_response = answer_with_tools(messages=messages, tools=[])
            _record_chat_token_usage(token_usage, last_response)
            yield _sse_event("token_usage", token_usage)

        content = str(last_response.get("content") or "").strip()
        if not content:
            content = "I could not find enough evidence in the documents."
        response = ChatResponse(
            message=ChatMessageRequest(role="assistant", content=content),
            citations=_extract_tool_citations(tool_payloads),
            tool_calls=tool_calls_for_response,
            token_usage=ChatTokenUsageResponse(**token_usage),
            debug={"steps": debug_steps} if payload.debug else None,
        )
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
        else:
            detail = str(exc)
        yield _sse_event("error", {"detail": detail})


@router.post("/chat", response_model=ChatResponse)
def chat_all_documents_endpoint(
    payload: ChatRequest,
    repository: DocumentRepository = Depends(document_repository_dependency),
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
    repository: DocumentRepository = Depends(document_repository_dependency),
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
