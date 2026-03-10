import json
from typing import Any

import httpx

from paperwise.application.interfaces import LLMProvider


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
            "tags must be an array of strings. "
            "Use natural casing: title case for normal words, but preserve acronyms in uppercase "
            "(for example: PPMG Pediatrics, IRS Notice). "
            "Keep original casing when already meaningful; only normalize when text is all lowercase. "
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
                "Use title case for normal words in document_type/tags, "
                "but keep acronyms uppercase (for example: PPMG Pediatrics, IRS). "
                "Keep original casing when already meaningful; only normalize casing when all words are lowercase. "
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

        result: dict[str, Any] = {}

        suggested_title = parsed.get("suggested_title")
        if isinstance(suggested_title, str) and suggested_title.strip():
            result["suggested_title"] = suggested_title.strip()

        if "document_date" in parsed:
            result["document_date"] = parsed.get("document_date")

        correspondent = parsed.get("correspondent")
        if isinstance(correspondent, str) and correspondent.strip():
            result["correspondent"] = correspondent.strip()

        document_type = parsed.get("document_type")
        if isinstance(document_type, str) and document_type.strip():
            result["document_type"] = document_type.strip()

        tags = parsed.get("tags")
        if isinstance(tags, list):
            result["tags"] = [str(tag) for tag in tags if str(tag).strip()]

        return result
