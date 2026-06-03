from collections.abc import Iterator
from dataclasses import dataclass
import json
import logging
import time
from typing import Any
from uuid import uuid4

from paperwise.application.interfaces import LLMProvider
from paperwise.application.services.chat_tools import ChatToolRepository, ChatToolScope, execute_chat_tool
from paperwise.domain.models import User
from paperwise.infrastructure.llm.debug_log import log_llm_exchange

INITIAL_LOCAL_SEARCH_MAX_CHUNKS = 8
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatRuntimeResult:
    content: str
    tool_payloads: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    token_usage: dict[str, int]
    debug_steps: list[dict[str, Any]]


@dataclass(frozen=True)
class ChatRuntimeEvent:
    type: str
    data: dict[str, Any] | ChatRuntimeResult


class ChatRuntimeUnsupportedError(RuntimeError):
    pass


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


def _latest_user_query(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if str(message.get("role") or "").strip().lower() != "user":
            continue
        content = " ".join(str(message.get("content") or "").split()).strip()
        if content:
            return content
    return ""


def _append_initial_local_search_context(
    *,
    repository: ChatToolRepository,
    llm_provider: LLMProvider,
    current_user: User,
    messages: list[dict[str, Any]],
    scope: ChatToolScope,
    top_k_chunks: int,
    max_documents: int,
) -> None:
    query = _latest_user_query(messages)
    if not query:
        return
    started_at = time.perf_counter()
    limit = max(1, min(INITIAL_LOCAL_SEARCH_MAX_CHUNKS, top_k_chunks))
    result = execute_chat_tool(
        repository=repository,
        llm_provider=llm_provider,
        current_user=current_user,
        scope=scope,
        top_k_chunks=limit,
        max_documents=max_documents,
        name="search_document_chunks",
        arguments={"query": query, "limit": limit},
    )
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    _debug_chat_timing(
        stage="initial_local_search",
        elapsed_ms=elapsed_ms,
        result_count=int(result.get("total_results") or result.get("returned_results") or 0),
        scope_document_count=result.get("scope_document_count"),
    )
    payload = {
        "query": query,
        "search_strategy": "local_heuristic",
        "result": result,
    }
    messages.insert(
        1,
        {
            "role": "system",
            "content": (
                "Initial local document search for the latest user message has already run. "
                "Use these preliminary OCR chunk results if they contain enough evidence. "
                "If they are incomplete or poorly targeted, call search_document_chunks with "
                "your own rewritten query or metadata filters. JSON: "
                f"{json.dumps(payload)}"
            ),
        },
    )


def _debug_chat_timing(*, stage: str, elapsed_ms: float, **fields: Any) -> None:
    payload = {
        "stage": stage,
        "elapsed_ms": round(elapsed_ms, 1),
        **{
            key: value
            for key, value in fields.items()
            if isinstance(value, (str, int, float, bool)) or value is None
        },
    }
    log_llm_exchange(
        provider="chat_runtime",
        endpoint="debug/timing",
        request_payload=payload,
    )
    if not logger.isEnabledFor(logging.DEBUG):
        return
    safe_fields = " ".join(
        f"{key}={value}"
        for key, value in sorted(payload.items())
        if key not in {"stage", "elapsed_ms"}
    )
    suffix = f" {safe_fields}" if safe_fields else ""
    logger.debug("chat_runtime_timing stage=%s elapsed_ms=%.1f%s", stage, elapsed_ms, suffix)


def iter_chat_runtime_events(
    *,
    repository: ChatToolRepository,
    llm_provider: LLMProvider,
    current_user: User,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    scope: ChatToolScope,
    top_k_chunks: int,
    max_documents: int,
    max_tool_rounds: int,
    max_tool_calls: int = 8,
) -> Iterator[ChatRuntimeEvent]:
    answer_with_tools = getattr(llm_provider, "answer_with_tools", None)
    if not callable(answer_with_tools):
        raise ChatRuntimeUnsupportedError(
            "Selected Grounded Q&A provider does not support conversational tool use."
        )

    tool_calls_for_response: list[dict[str, Any]] = []
    tool_payloads: list[dict[str, Any]] = []
    debug_steps: list[dict[str, Any]] = []
    token_usage: dict[str, int] = {"total_tokens": 0, "llm_requests": 0}
    last_response: dict[str, Any] = {}
    exhausted_tool_rounds = False

    yield ChatRuntimeEvent(
        "status",
        {"label": "Local search", "detail": "Searching OCR chunks before the first LLM request."},
    )
    _append_initial_local_search_context(
        repository=repository,
        llm_provider=llm_provider,
        current_user=current_user,
        messages=messages,
        scope=scope,
        top_k_chunks=top_k_chunks,
        max_documents=max_documents,
    )

    for round_index in range(max_tool_rounds):
        if tool_calls_for_response:
            status_detail = (
                f"Reading {len(tool_calls_for_response)} tool result(s) and writing an answer, "
                f"round {round_index + 1}."
            )
        else:
            status_detail = f"Choosing document tools, round {round_index + 1}."
        yield ChatRuntimeEvent("status", {"label": "LLM request", "detail": status_detail})

        started_at = time.perf_counter()
        last_response = answer_with_tools(messages=messages, tools=tools)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        _record_chat_token_usage(token_usage, last_response)
        tool_calls = last_response.get("tool_calls", []) if isinstance(last_response, dict) else []
        _debug_chat_timing(
            stage="llm_tool_round",
            elapsed_ms=elapsed_ms,
            round=round_index + 1,
            tool_call_count=len(tool_calls),
            llm_requests=token_usage.get("llm_requests", 0),
            total_tokens=token_usage.get("total_tokens", 0),
        )
        yield ChatRuntimeEvent(
            "llm_response",
            {
                "label": "LLM response",
                "tool_call_count": len(tool_calls),
                "token_usage": token_usage,
            },
        )
        yield ChatRuntimeEvent("token_usage", dict(token_usage))
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
            yield ChatRuntimeEvent("tool_call", {"name": name, "arguments": arguments})
            started_at = time.perf_counter()
            result = execute_chat_tool(
                repository=repository,
                llm_provider=llm_provider,
                current_user=current_user,
                scope=scope,
                top_k_chunks=top_k_chunks,
                max_documents=max_documents,
                name=name,
                arguments=arguments,
            )
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            tool_payloads.append(result)
            tool_results.append((call_id, name, result))
            result_count = int(result.get("total_results") or result.get("returned_results") or 0)
            _debug_chat_timing(
                stage="tool_execution",
                elapsed_ms=elapsed_ms,
                tool=name,
                result_count=result_count,
            )
            tool_calls_for_response.append(
                {"name": name, "arguments": arguments, "result_count": result_count}
            )
            debug_steps.append({"tool": name, "arguments": arguments, "result": result})
            yield ChatRuntimeEvent("tool_result", {"name": name, "result_count": result_count})

        _append_chat_tool_messages(
            messages=messages,
            last_response=last_response,
            assistant_tool_calls=assistant_tool_calls,
            tool_results=tool_results,
        )
        if len(tool_calls_for_response) >= max_tool_calls:
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
        yield ChatRuntimeEvent(
            "status",
            {"label": "LLM request", "detail": "Writing final answer from collected tool results."},
        )
        started_at = time.perf_counter()
        last_response = answer_with_tools(messages=messages, tools=[])
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        _record_chat_token_usage(token_usage, last_response)
        _debug_chat_timing(
            stage="llm_final_from_exhausted_tools",
            elapsed_ms=elapsed_ms,
            llm_requests=token_usage.get("llm_requests", 0),
            total_tokens=token_usage.get("total_tokens", 0),
        )
        yield ChatRuntimeEvent("token_usage", dict(token_usage))

    content = str(last_response.get("content") or "").strip()
    if not content:
        content = "I could not find enough evidence in the documents."
    yield ChatRuntimeEvent(
        "final",
        ChatRuntimeResult(
            content=content,
            tool_payloads=tool_payloads,
            tool_calls=tool_calls_for_response,
            token_usage=token_usage,
            debug_steps=debug_steps,
        ),
    )


def run_chat_runtime(**kwargs: Any) -> ChatRuntimeResult:
    final_result: ChatRuntimeResult | None = None
    for event in iter_chat_runtime_events(**kwargs):
        if event.type == "final":
            final_result = event.data if isinstance(event.data, ChatRuntimeResult) else None
    if final_result is None:
        raise RuntimeError("Chat runtime ended without a final response.")
    return final_result
