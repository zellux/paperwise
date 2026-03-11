from typing import Any

from paperwise.application.interfaces import LLMProvider


class MissingOpenAIProvider(LLMProvider):
    def extract_ocr_text(
        self,
        *,
        filename: str,
        content_type: str,
        text_preview: str,
    ) -> str:
        del filename
        del content_type
        del text_preview
        raise RuntimeError(
            "LLM OCR requires a configured provider. Set LLM provider and API key in Settings."
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
        del filename
        del text_preview
        del current_correspondent
        del current_document_type
        del existing_correspondents
        del existing_document_types
        del existing_tags
        raise RuntimeError(
            "LLM parse requires a configured provider. Set provider and API key in Settings."
        )

    def answer_grounded(
        self,
        *,
        question: str,
        contexts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        del question
        del contexts
        raise RuntimeError(
            "Grounded Q&A requires a configured LLM provider. Set provider and API key in Settings."
        )

    def rewrite_retrieval_queries(
        self,
        *,
        question: str,
    ) -> dict[str, Any]:
        del question
        raise RuntimeError(
            "Grounded Q&A query rewrite requires a configured LLM provider. Set provider and API key in Settings."
        )
