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


class GeminiLLMProvider(LLMProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers={"content-type": "application/json"},
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
        endpoint = f"/models/{self._model}:generateContent?key={self._api_key}"
        request_payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": json.dumps(user_prompt)}],
                }
            ],
            "generationConfig": {"temperature": 0},
        }
        response: httpx.Response | None = None
        response_payload: Any = None

        try:
            response = self._client.post(endpoint, json=request_payload)
            try:
                response_payload = response.json()
            except ValueError:
                response_payload = {"raw_text": getattr(response, "text", "")}
        except Exception as exc:
            log_llm_exchange(
                provider="gemini",
                endpoint=f"/models/{self._model}:generateContent",
                request_payload=request_payload,
                error=str(exc),
            )
            raise

        log_llm_exchange(
            provider="gemini",
            endpoint=f"/models/{self._model}:generateContent",
            request_payload=request_payload,
            response_status=getattr(response, "status_code", None),
            response_payload=response_payload,
        )
        response.raise_for_status()
        payload = response_payload if isinstance(response_payload, dict) else response.json()
        candidates = payload.get("candidates", [])
        candidate = candidates[0] if candidates else {}
        content = candidate.get("content", {}) if isinstance(candidate, dict) else {}
        parts = content.get("parts", []) if isinstance(content, dict) else []
        text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
        parsed = json.loads(text.strip())

        result = extract_metadata_result(parsed)

        usage = payload.get("usageMetadata", {})
        total_tokens = usage.get("totalTokenCount")
        if isinstance(total_tokens, int) and total_tokens > 0:
            result["llm_total_tokens"] = total_tokens
        return result
