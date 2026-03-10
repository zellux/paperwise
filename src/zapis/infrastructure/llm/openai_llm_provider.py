import json
from typing import Any

import httpx

from zapis.application.interfaces import LLMProvider


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
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict[str, Any]:
        system_prompt = (
            "You extract metadata for scanned documents. "
            "Return strict JSON with keys: suggested_title, document_date, "
            "correspondent, document_type, tags. "
            "document_date must be YYYY-MM-DD or null. "
            "correspondent must be the sender/issuer of the document "
            "(for example bank, utility, insurer, lab, credit bureau, clinic), "
            "not the recipient/customer. "
            "If sender is ambiguous, choose the strongest issuer signal from letterhead, "
            "logo, signature block, or footer and avoid generic placeholders. "
            "tags must be an array of strings in Title Case (for example: Credit Report). "
            "When reusing existing taxonomy names, copy the existing names exactly."
        )
        user_prompt = {
            "filename": filename,
            "text_preview": text_preview,
            "existing_correspondents": existing_correspondents,
            "existing_document_types": existing_document_types,
            "existing_tags": existing_tags,
            "guidance": (
                "Prefer existing taxonomy names when appropriate. "
                "Only propose new names when no existing option is a good match. "
                "Use Title Case for document_type and every tag (for example: Credit Report). "
                "For correspondent: normalize punctuation/suffixes (e.g. 'Experian.' -> 'Experian'), "
                "prefer organization names over department names, and never return the document owner."
            ),
        }

        response = self._client.post(
            "/chat/completions",
            json={
                "model": self._model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_prompt)},
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        tags = parsed.get("tags")
        if not isinstance(tags, list):
            tags = []

        return {
            "suggested_title": str(parsed.get("suggested_title") or filename),
            "document_date": parsed.get("document_date"),
            "correspondent": str(parsed.get("correspondent") or "Unknown Sender"),
            "document_type": str(parsed.get("document_type") or "General Document"),
            "tags": [str(tag) for tag in tags if str(tag).strip()],
        }
