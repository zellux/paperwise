import json
from typing import Any

import httpx

from paperwise.application.interfaces import LLMProvider
from paperwise.infrastructure.llm.metadata_prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
    extract_metadata_result,
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

        response = self._client.post(
            "/v1/messages",
            json={
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
            },
        )
        response.raise_for_status()
        payload = response.json()
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
