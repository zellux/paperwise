import json
from typing import Any

import httpx

from paperwise.application.interfaces import LLMProvider
from paperwise.infrastructure.llm.metadata_prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
    extract_metadata_result,
)


class OpenAILLMProvider(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._model = model
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
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
            "/chat/completions",
            json={
                "model": self._model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(user_prompt)},
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        usage = payload.get("usage", {})

        result = extract_metadata_result(parsed)

        total_tokens = usage.get("total_tokens")
        if isinstance(total_tokens, int) and total_tokens > 0:
            result["llm_total_tokens"] = total_tokens

        return result
