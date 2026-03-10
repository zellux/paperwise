import json
from typing import Any

import httpx

from paperwise.application.interfaces import LLMProvider
from paperwise.infrastructure.llm.debug_log import log_llm_exchange
from paperwise.infrastructure.llm.metadata_prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
    extract_metadata_result,
)
from paperwise.infrastructure.llm.ocr_prompt import (
    OCR_SYSTEM_PROMPT,
    build_ocr_user_prompt,
    extract_ocr_text_result,
)
from paperwise.infrastructure.llm.grounded_qa_prompt import (
    GROUNDED_QA_SYSTEM_PROMPT,
    build_grounded_qa_user_prompt,
    extract_grounded_qa_result,
)


class AnthropicLLMProvider(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.anthropic.com",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._model = model
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )

    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        current_correspondent: str | None,
        current_document_type: str | None,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict[str, Any]:
        user_prompt = build_user_prompt(
            filename=filename,
            text_preview=text_preview,
            current_correspondent=current_correspondent,
            current_document_type=current_document_type,
            existing_correspondents=existing_correspondents,
            existing_document_types=existing_document_types,
            existing_tags=existing_tags,
        )
        request_payload = {
            "model": self._model,
            "max_tokens": 1000,
            "temperature": 0,
            "system": SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps(user_prompt),
                }
            ],
        }
        response: httpx.Response | None = None
        response_payload: Any = None

        try:
            response = self._client.post("/v1/messages", json=request_payload)
            try:
                response_payload = response.json()
            except ValueError:
                response_payload = {"raw_text": getattr(response, "text", "")}
        except Exception as exc:
            log_llm_exchange(
                provider="claude",
                endpoint="/v1/messages",
                request_payload=request_payload,
                error=str(exc),
            )
            raise

        log_llm_exchange(
            provider="claude",
            endpoint="/v1/messages",
            request_payload=request_payload,
            response_status=getattr(response, "status_code", None),
            response_payload=response_payload,
        )
        response.raise_for_status()
        payload = response_payload if isinstance(response_payload, dict) else response.json()
        content_blocks = payload.get("content", [])
        text_chunks = [
            str(block.get("text", ""))
            for block in content_blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        parsed = json.loads("".join(text_chunks).strip())

        result = extract_metadata_result(parsed)

        usage = payload.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_tokens = 0
        if isinstance(input_tokens, int) and input_tokens > 0:
            total_tokens += input_tokens
        if isinstance(output_tokens, int) and output_tokens > 0:
            total_tokens += output_tokens
        if total_tokens > 0:
            result["llm_total_tokens"] = total_tokens
        return result

    def extract_ocr_text(
        self,
        *,
        filename: str,
        content_type: str,
        text_preview: str,
    ) -> str:
        user_prompt = build_ocr_user_prompt(
            filename=filename,
            content_type=content_type,
            text_preview=text_preview,
        )
        request_payload = {
            "model": self._model,
            "max_tokens": 3000,
            "temperature": 0,
            "system": OCR_SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps(user_prompt),
                }
            ],
        }
        response: httpx.Response | None = None
        response_payload: Any = None

        try:
            response = self._client.post("/v1/messages", json=request_payload)
            try:
                response_payload = response.json()
            except ValueError:
                response_payload = {"raw_text": getattr(response, "text", "")}
        except Exception as exc:
            log_llm_exchange(
                provider="claude",
                endpoint="/v1/messages",
                request_payload=request_payload,
                error=str(exc),
            )
            raise

        log_llm_exchange(
            provider="claude",
            endpoint="/v1/messages",
            request_payload=request_payload,
            response_status=getattr(response, "status_code", None),
            response_payload=response_payload,
        )
        response.raise_for_status()
        payload = response_payload if isinstance(response_payload, dict) else response.json()
        content_blocks = payload.get("content", [])
        text_chunks = [
            str(block.get("text", ""))
            for block in content_blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        content = "".join(text_chunks).strip()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return content

        extracted = extract_ocr_text_result(parsed)
        return extracted or content

    def answer_grounded(
        self,
        *,
        question: str,
        contexts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        user_prompt = build_grounded_qa_user_prompt(question=question, contexts=contexts)
        request_payload = {
            "model": self._model,
            "max_tokens": 2000,
            "temperature": 0,
            "system": GROUNDED_QA_SYSTEM_PROMPT,
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps(user_prompt),
                }
            ],
        }
        response: httpx.Response | None = None
        response_payload: Any = None
        try:
            response = self._client.post("/v1/messages", json=request_payload)
            try:
                response_payload = response.json()
            except ValueError:
                response_payload = {"raw_text": getattr(response, "text", "")}
        except Exception as exc:
            log_llm_exchange(
                provider="claude",
                endpoint="/v1/messages",
                request_payload=request_payload,
                error=str(exc),
            )
            raise

        log_llm_exchange(
            provider="claude",
            endpoint="/v1/messages",
            request_payload=request_payload,
            response_status=getattr(response, "status_code", None),
            response_payload=response_payload,
        )
        response.raise_for_status()
        payload = response_payload if isinstance(response_payload, dict) else response.json()
        content_blocks = payload.get("content", [])
        text_chunks = [
            str(block.get("text", ""))
            for block in content_blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        parsed = json.loads("".join(text_chunks).strip())
        result = extract_grounded_qa_result(parsed)
        usage = payload.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_tokens = 0
        if isinstance(input_tokens, int) and input_tokens > 0:
            total_tokens += input_tokens
        if isinstance(output_tokens, int) and output_tokens > 0:
            total_tokens += output_tokens
        if total_tokens > 0:
            result["llm_total_tokens"] = total_tokens
        return result
