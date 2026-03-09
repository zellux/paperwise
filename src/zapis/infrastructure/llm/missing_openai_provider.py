from typing import Any

from zapis.application.interfaces import LLMProvider


class MissingOpenAIProvider(LLMProvider):
    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict[str, Any]:
        del filename
        del text_preview
        del existing_correspondents
        del existing_document_types
        del existing_tags
        raise RuntimeError(
            "OpenAI provider is required for llm-parse. Set ZAPIS_OPENAI_API_KEY in .env.local."
        )

