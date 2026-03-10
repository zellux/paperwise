from paperwise.application.interfaces import LLMProvider


class BaseLLMAdapter(LLMProvider):
    def suggest_metadata(
        self,
        *,
        filename: str,
        text_preview: str,
        existing_correspondents: list[str],
        existing_document_types: list[str],
        existing_tags: list[str],
    ) -> dict:
        raise NotImplementedError
