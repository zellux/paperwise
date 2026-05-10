from collections.abc import Iterator
from dataclasses import dataclass
import json
from typing import Any
from uuid import uuid4

from paperwise.application.interfaces import LLMProvider
from paperwise.application.services.chat_tools import ChatToolRepository, ChatToolScope, execute_chat_tool
from paperwise.domain.models import User


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

    for round_index in range(max_tool_rounds):
        if tool_calls_for_response:
            status_detail = (
                f"Reading {len(tool_calls_for_response)} tool result(s) and writing an answer, "
                f"round {round_index + 1}."
            )
        else:
            status_detail = f"Choosing document tools, round {round_index + 1}."
        yield ChatRuntimeEvent("status", {"label": "LLM request", "detail": status_detail})

        last_response = answer_with_tools(messages=messages, tools=tools)
        _record_chat_token_usage(token_usage, last_response)
        tool_calls = last_response.get("tool_calls", []) if isinstance(last_response, dict) else []
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
            tool_payloads.append(result)
            tool_results.append((call_id, name, result))
            result_count = int(result.get("total_results") or result.get("returned_results") or 0)
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
        last_response = answer_with_tools(messages=messages, tools=[])
        _record_chat_token_usage(token_usage, last_response)
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
