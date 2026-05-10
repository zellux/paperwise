from __future__ import annotations

from paperwise.application.interfaces import LLMProvider


def get_llm_provider_model(llm_provider: LLMProvider | None) -> str | None:
    if llm_provider is None:
        return None
    for attr_name in ("_model", "model"):
        value = getattr(llm_provider, attr_name, None)
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                return cleaned
    return None


def get_llm_provider_base_url(llm_provider: LLMProvider | None) -> str | None:
    if llm_provider is None:
        return None
    client = getattr(llm_provider, "_client", None)
    base_url = getattr(client, "base_url", None)
    if base_url is None:
        return None
    cleaned = str(base_url).strip().rstrip("/")
    return cleaned or None


def get_llm_provider_name(llm_provider: LLMProvider | None) -> str | None:
    if llm_provider is None:
        return None
    class_name = llm_provider.__class__.__name__
    if class_name == "GeminiLLMProvider":
        return "gemini"
    if class_name == "OpenAILLMProvider":
        base_url = (get_llm_provider_base_url(llm_provider) or "").casefold()
        if base_url.endswith("/v1") and "api.openai.com" in base_url:
            return "openai"
        if base_url:
            return "custom"
        return "openai"
    if class_name == "SimpleLLMProvider":
        return "simple"
    if class_name.endswith("LLMProvider"):
        normalized = class_name[: -len("LLMProvider")].strip()
        if normalized:
            return normalized.casefold()
    return class_name.casefold() or None


def summarize_llm_provider(llm_provider: LLMProvider | None) -> dict[str, str | None]:
    return {
        "provider": get_llm_provider_name(llm_provider),
        "model": get_llm_provider_model(llm_provider),
        "base_url": get_llm_provider_base_url(llm_provider),
    }
