from typing import Any

from paperwise.application.interfaces import LLMProvider


class MissingOpenAIProvider(LLMProvider):
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
        del filename
        del text_preview
        del current_correspondent
        del current_document_type
        del existing_correspondents
        del existing_document_types
        del existing_tags
        raise RuntimeError(
            "OpenAI provider is required for llm-parse. Set PAPERWISE_OPENAI_API_KEY in .env.local."
        )
