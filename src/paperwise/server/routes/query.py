import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from paperwise.application.interfaces import DocumentRepository, LLMProvider
from paperwise.application.services.llm_preferences import LLM_TASK_GROUNDED_QA
from paperwise.domain.models import ChatThread, User, UserPreference
from paperwise.server.dependencies import (
    current_user_dependency,
    document_repository_dependency,
    llm_provider_dependency,
)
from paperwise.server.routes.collections import (
    _build_qa_contexts,
    _is_timeout_error,
    _resolve_metadata_scoped_document_ids,
    _search_document_chunks_multi_query,
)
from paperwise.server.routes.documents import _resolve_llm_provider_from_preferences

router = APIRouter(prefix="/query", tags=["query"])


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


CHAT_SYSTEM_PROMPT = (
    "You are Paperwise's conversational document assistant. Use the available tools to inspect the user's "
    "documents, tags, metadata, and grounded text chunks. Do not answer from outside knowledge. For document "
    "content claims, cite returned source titles or chunk IDs in your Markdown answer. Always query across all "
    "owner-visible documents unless a metadata filter is needed. If the tools return no useful evidence, say "
    "that the documents do not contain enough evidence. Prefer metadata tools for "
    "questions about counts, available tags, document types, dates, correspondents, or document lists."
)
MAX_CHAT_TOOL_ROUNDS = 3
CHAT_SEARCH_CONTEXT_MAX_CHARS = 1800
CHAT_CONTEXT_PREFIX_CHARS = 420
CHAT_THREADS_PREFERENCE_KEY = "chat_threads"
MAX_CHAT_THREADS = 20
MAX_STORED_CHAT_MESSAGES = 40
MAX_STORED_CHAT_MESSAGE_CHARS = 8000


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
    title = str(thread.get("title") or "").strip() or _thread_title_from_messages(messages)
    return ChatThread(
        id=thread_id,
        owner_id=current_user.id,
        title=title[:256] or "Untitled chat",
        messages=messages[-MAX_STORED_CHAT_MESSAGES:],
        token_usage=token_usage,
        created_at=created_at,
        updated_at=updated_at,
    )


def _migrate_legacy_chat_threads(repository: DocumentRepository, current_user: User) -> None:
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


def _thread_title_from_messages(messages: list[dict[str, Any]]) -> str:
    for message in messages:
        if message.get("role") != "user":
            continue
        content = " ".join(str(message.get("content") or "").split())
        if content:
            return content[:80]
    return "New chat"


def _truncate_stored_chat_content(value: str) -> str:
    content = str(value or "").strip()
    if len(content) <= MAX_STORED_CHAT_MESSAGE_CHARS:
        return content
    return content[:MAX_STORED_CHAT_MESSAGE_CHARS].rstrip() + "\n\n[truncated]"


def _stored_chat_messages(payload: ChatRequest, response: ChatResponse) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for message in payload.messages:
        role = message.role.strip().lower()
        content = message.content.strip()
        if role not in {"user", "assistant"} or not content:
            continue
        messages.append({"role": role, "content": _truncate_stored_chat_content(content)})
    assistant_message: dict[str, Any] = {
        "role": "assistant",
        "content": _truncate_stored_chat_content(response.message.content),
    }
    if response.citations:
        assistant_message["citations"] = [citation.model_dump(mode="json") for citation in response.citations]
    messages.append(assistant_message)
    return messages[-MAX_STORED_CHAT_MESSAGES:]


def _save_chat_thread(
    *,
    repository: DocumentRepository,
    current_user: User,
    payload: ChatRequest,
    response: ChatResponse,
) -> ChatResponse:
    _migrate_legacy_chat_threads(repository, current_user)
    thread_id = (payload.thread_id or "").strip() or str(uuid4())
    now = datetime.now(UTC)
    previous = repository.get_chat_thread(current_user.id, thread_id)
    messages = _stored_chat_messages(payload, response)
    title = previous.title.strip() if previous is not None else _thread_title_from_messages(messages)
    repository.save_chat_thread(
        ChatThread(
            id=thread_id,
            owner_id=current_user.id,
            title=(title or _thread_title_from_messages(messages))[:256],
            messages=messages,
            token_usage=response.token_usage.model_dump(mode="json"),
            created_at=previous.created_at if previous is not None else now,
            updated_at=now,
        )
    )
    response.thread_id = thread_id
    return response


def _to_chat_thread_summary(thread: ChatThread) -> ChatThreadSummaryResponse:
    return ChatThreadSummaryResponse(
        id=thread.id,
        title=thread.title or "Untitled chat",
        message_count=len(thread.messages),
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
    )


def _to_chat_thread_response(thread: ChatThread) -> ChatThreadResponse:
    summary = _to_chat_thread_summary(thread)
    usage = dict(thread.token_usage or {})
    return ChatThreadResponse(
        **summary.model_dump(mode="json"),
        messages=[dict(message) for message in thread.messages],
        token_usage=ChatTokenUsageResponse(
            total_tokens=int(usage.get("total_tokens") or 0),
            llm_requests=int(usage.get("llm_requests") or 0),
        ),
    )


@router.get("/chat/threads", response_model=list[ChatThreadSummaryResponse])
def list_chat_threads_endpoint(
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> list[ChatThreadSummaryResponse]:
    _migrate_legacy_chat_threads(repository, current_user)
    return [_to_chat_thread_summary(thread) for thread in repository.list_chat_threads(current_user.id, MAX_CHAT_THREADS)]


@router.get("/chat/threads/{thread_id}", response_model=ChatThreadResponse)
def get_chat_thread_endpoint(
    thread_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> ChatThreadResponse:
    _migrate_legacy_chat_threads(repository, current_user)
    thread = repository.get_chat_thread(current_user.id, thread_id)
    if thread is not None:
        return _to_chat_thread_response(thread)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat thread not found.")


@router.delete("/chat/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_thread_endpoint(
    thread_id: str,
    repository: DocumentRepository = Depends(document_repository_dependency),
    current_user: User = Depends(current_user_dependency),
) -> Response:
    _migrate_legacy_chat_threads(repository, current_user)
    if not repository.delete_chat_thread(current_user.id, thread_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat thread not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _merge_tool_filters(scope: ChatScopeRequest, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "tag": list(scope.tag or []) + [str(item) for item in arguments.get("tags", []) if str(item).strip()],
        "document_type": list(scope.document_type or [])
        + [str(item) for item in arguments.get("document_types", []) if str(item).strip()],
        "correspondent": list(scope.correspondent or [])
        + [str(item) for item in arguments.get("correspondents", []) if str(item).strip()],
        "date_from": arguments.get("date_from") or scope.date_from,
        "date_to": arguments.get("date_to") or scope.date_to,
    }


def _to_tool_document_item(repository: DocumentRepository, document_id: str) -> dict[str, Any] | None:
    document = repository.get(document_id)
    if document is None:
        return None
    llm = repository.get_llm_parse_result(document_id)
    return {
        "document_id": document.id,
        "filename": document.filename,
        "title": llm.suggested_title if llm is not None and llm.suggested_title else document.filename,
        "document_date": llm.document_date if llm is not None else None,
        "document_type": llm.document_type if llm is not None else None,
        "correspondent": llm.correspondent if llm is not None else None,
        "tags": list(llm.tags or []) if llm is not None else [],
        "created_at": document.created_at.isoformat(),
    }


def _all_owned_document_ids(repository: DocumentRepository, current_user: User) -> list[str]:
    return [
        document.id
        for document in repository.list_documents(limit=10_000)
        if document.owner_id == current_user.id
    ]


def _extract_chat_query_terms(query: str) -> list[str]:
    terms = []
    for term in re.findall(r"[\w\u4e00-\u9fff']+", query.casefold()):
        if len(term) >= 3 or re.search(r"[\u4e00-\u9fff]", term):
            terms.append(term)
    return terms


def _compact_chat_context_content(content: str, query: str) -> tuple[str, bool]:
    text = str(content or "")
    if len(text) <= CHAT_SEARCH_CONTEXT_MAX_CHARS:
        return text, False
    lowered = text.casefold()
    match_index = -1
    for term in _extract_chat_query_terms(query):
        index = lowered.find(term)
        if index != -1 and (match_index == -1 or index < match_index):
            match_index = index
    if match_index == -1:
        start = 0
    else:
        start = max(0, match_index - CHAT_CONTEXT_PREFIX_CHARS)
    end = min(len(text), start + CHAT_SEARCH_CONTEXT_MAX_CHARS)
    if end == len(text):
        start = max(0, end - CHAT_SEARCH_CONTEXT_MAX_CHARS)
    excerpt = text[start:end].strip()
    if start > 0:
        excerpt = f"... {excerpt}"
    if end < len(text):
        excerpt = f"{excerpt} ..."
    return excerpt, True


def _compact_chat_search_contexts(contexts: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    compacted = []
    for context in contexts:
        content, truncated = _compact_chat_context_content(str(context.get("content") or ""), query)
        item = dict(context)
        item["content"] = content
        if truncated:
            item["content_truncated"] = True
            item["source_content_chars"] = len(str(context.get("content") or ""))
        compacted.append(item)
    return compacted


def _execute_chat_tool(
    *,
    repository: DocumentRepository,
    llm_provider: LLMProvider,
    current_user: User,
    scope: ChatScopeRequest,
    top_k_chunks: int,
    max_documents: int,
    name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    merged_filters = _merge_tool_filters(scope, arguments)
    scoped_ids = _resolve_metadata_scoped_document_ids(
        repository=repository,
        current_user=current_user,
        base_document_ids=None,
        tag_filters=merged_filters["tag"],
        document_type_filters=merged_filters["document_type"],
        correspondent_filters=merged_filters["correspondent"],
        date_from=merged_filters["date_from"],
        date_to=merged_filters["date_to"],
        title_query=str(arguments.get("title_query") or ""),
    )
    if name == "search_document_chunks":
        query = " ".join(str(arguments.get("query") or "").split()).strip()
        limit = max(1, min(60, int(arguments.get("limit") or top_k_chunks)))
        hits = _search_document_chunks_multi_query(
            repository=repository,
            owner_id=current_user.id,
            query=query,
            limit=max(limit * 3, limit),
            document_ids=scoped_ids,
            llm_provider=llm_provider,
        )
        contexts = _build_qa_contexts(
            repository=repository,
            chunk_hits=hits,
            top_k_chunks=limit,
            max_documents=max_documents,
        )
        contexts = _compact_chat_search_contexts(contexts, query)
        return {
            "results": contexts,
            "total_results": len(contexts),
            "scope_document_count": len(scoped_ids) if scoped_ids is not None else None,
        }
    if name == "query_document_metadata":
        limit = max(1, min(100, int(arguments.get("limit") or 25)))
        document_ids = scoped_ids if scoped_ids is not None else _all_owned_document_ids(repository, current_user)
        items = []
        for document_id in document_ids[:limit]:
            item = _to_tool_document_item(repository, document_id)
            if item is not None:
                items.append(item)
        return {"documents": items, "total_results": len(document_ids), "returned_results": len(items)}
    if name == "summarize_taxonomy":
        document_ids = scoped_ids if scoped_ids is not None else _all_owned_document_ids(repository, current_user)
        tag_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}
        correspondent_counts: dict[str, int] = {}
        for document_id in document_ids:
            llm = repository.get_llm_parse_result(document_id)
            if llm is None:
                continue
            for tag in llm.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            type_counts[llm.document_type] = type_counts.get(llm.document_type, 0) + 1
            correspondent_counts[llm.correspondent] = correspondent_counts.get(llm.correspondent, 0) + 1

        def top_items(counts: dict[str, int]) -> list[dict[str, Any]]:
            return [
                {"name": item_name, "document_count": count}
                for item_name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold()))[:30]
            ]

        return {
            "document_count": len(document_ids),
            "tags": top_items(tag_counts),
            "document_types": top_items(type_counts),
            "correspondents": top_items(correspondent_counts),
        }
    if name == "get_document_context":
        document_id = str(arguments.get("document_id") or "").strip()
        document = repository.get(document_id)
        if document is None or document.owner_id != current_user.id:
            return {"error": "Document not found."}
        max_chunks = max(1, min(20, int(arguments.get("max_chunks") or 8)))
        metadata = _to_tool_document_item(repository, document_id)
        chunks = [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "title": metadata["title"] if metadata else document.filename,
                "content": chunk.content[:2500],
            }
            for chunk in repository.list_document_chunks(document_id)[:max_chunks]
        ]
        return {"document": metadata, "chunks": chunks, "total_results": len(chunks)}
    return {"error": f"Unknown tool: {name}"}


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


def _record_chat_token_usage(token_usage: dict[str, int], response: dict[str, Any]) -> None:
    total_tokens = response.get("llm_total_tokens") if isinstance(response, dict) else None
    if not isinstance(total_tokens, int) or total_tokens <= 0:
        return
    token_usage["total_tokens"] = token_usage.get("total_tokens", 0) + total_tokens
    token_usage["llm_requests"] = token_usage.get("llm_requests", 0) + 1


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
    for _ in range(MAX_CHAT_TOOL_ROUNDS):
        try:
            last_response = answer_with_tools(messages=messages, tools=CHAT_TOOLS)
            _record_chat_token_usage(token_usage, last_response)
        except Exception as exc:
            if _is_timeout_error(exc):
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
            call_id = str(call.get("id") or uuid4())
            name = str(call.get("name") or "").strip()
            raw_arguments = call.get("arguments", "{}")
            try:
                arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else dict(raw_arguments or {})
            except (TypeError, ValueError):
                arguments = {}
            assistant_tool_calls.append(
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(arguments)},
                }
            )
            result = _execute_chat_tool(
                repository=repository,
                llm_provider=llm_provider,
                current_user=current_user,
                scope=payload.scope,
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
            if _is_timeout_error(exc):
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
                call_id = str(call.get("id") or uuid4())
                name = str(call.get("name") or "").strip()
                raw_arguments = call.get("arguments", "{}")
                try:
                    arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else dict(raw_arguments or {})
                except (TypeError, ValueError):
                    arguments = {}
                assistant_tool_calls.append(
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(arguments)},
                    }
                )
                yield _sse_event("tool_call", {"name": name, "arguments": arguments})
                result = _execute_chat_tool(
                    repository=repository,
                    llm_provider=llm_provider,
                    current_user=current_user,
                    scope=payload.scope,
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
        if _is_timeout_error(exc):
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
    default_llm_provider: LLMProvider = Depends(llm_provider_dependency),
    current_user: User = Depends(current_user_dependency),
) -> ChatResponse:
    preference = repository.get_user_preference(current_user.id)
    preferences = dict(preference.preferences) if preference is not None else {}
    llm_provider = _resolve_llm_provider_from_preferences(
        preferences=preferences,
        default_llm_provider=default_llm_provider,
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
    default_llm_provider: LLMProvider = Depends(llm_provider_dependency),
    current_user: User = Depends(current_user_dependency),
) -> StreamingResponse:
    preference = repository.get_user_preference(current_user.id)
    preferences = dict(preference.preferences) if preference is not None else {}
    llm_provider = _resolve_llm_provider_from_preferences(
        preferences=preferences,
        default_llm_provider=default_llm_provider,
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
