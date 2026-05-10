from collections.abc import Callable
from typing import Any

from paperwise.application.interfaces import LLMProvider
from paperwise.application.services.llm_preferences import (
    LLM_TASK_METADATA,
    ResolvedLLMTaskConfig,
    default_base_url_for_provider,
    default_model_for_task,
    resolve_task_config,
    validate_api_key_for_provider,
)
from paperwise.infrastructure.llm.gemini_llm_provider import GeminiLLMProvider
from paperwise.infrastructure.llm.missing_openai_provider import MissingOpenAIProvider
from paperwise.infrastructure.llm.openai_llm_provider import OpenAILLMProvider
from paperwise.infrastructure.llm.simple_llm_provider import SimpleLLMProvider

ProviderErrorFactory = Callable[[str], Exception]


def resolve_llm_provider_from_preferences(
    *,
    preferences: dict[str, Any],
    default_llm_provider: LLMProvider,
    task: str = LLM_TASK_METADATA,
    missing_provider_detail: str = "Configure an LLM provider in Settings before running LLM parse.",
    missing_api_key_detail: str = "Selected LLM provider requires your API key in Settings.",
    missing_base_url_detail: str = "Custom LLM provider requires a base URL in Settings.",
    custom_response_format_type: str | None = None,
    error_factory: ProviderErrorFactory = RuntimeError,
) -> LLMProvider:
    config = resolve_task_config(preferences, task)
    ocr_image_detail = str(preferences.get("ocr_image_detail", "auto")).strip().lower()
    if ocr_image_detail not in {"auto", "low", "high"}:
        ocr_image_detail = "auto"
    return build_provider_from_task_config(
        config=config,
        default_llm_provider=default_llm_provider,
        task=task,
        ocr_image_detail=ocr_image_detail,
        missing_provider_detail=missing_provider_detail,
        missing_api_key_detail=missing_api_key_detail,
        missing_base_url_detail=missing_base_url_detail,
        custom_response_format_type=custom_response_format_type,
        error_factory=error_factory,
    )


def build_provider_from_task_config(
    *,
    config: ResolvedLLMTaskConfig | None,
    default_llm_provider: LLMProvider,
    task: str,
    ocr_image_detail: str = "auto",
    missing_provider_detail: str,
    missing_api_key_detail: str,
    missing_base_url_detail: str,
    custom_response_format_type: str | None = None,
    error_factory: ProviderErrorFactory = RuntimeError,
) -> LLMProvider:
    # Preserve testability when a fake provider is injected via dependency override.
    if not isinstance(
        default_llm_provider,
        (MissingOpenAIProvider, OpenAILLMProvider, GeminiLLMProvider, SimpleLLMProvider),
    ):
        return default_llm_provider

    if config is None or not config.provider:
        raise error_factory(missing_provider_detail)
    if not config.api_key:
        raise error_factory(missing_api_key_detail)
    api_key_error = validate_api_key_for_provider(config.provider, config.api_key)
    if api_key_error:
        raise error_factory(api_key_error)

    if config.provider == "openai":
        return OpenAILLMProvider(
            api_key=config.api_key,
            model=config.model or default_model_for_task("openai", task),
            base_url=config.base_url or default_base_url_for_provider("openai"),
            vision_image_detail=ocr_image_detail,
        )
    if config.provider == "gemini":
        return GeminiLLMProvider(
            api_key=config.api_key,
            model=config.model or default_model_for_task("gemini", task),
            base_url=config.base_url or default_base_url_for_provider("gemini"),
        )
    if config.provider == "custom":
        if not config.base_url:
            raise error_factory(missing_base_url_detail)
        return OpenAILLMProvider(
            api_key=config.api_key,
            model=config.model or default_model_for_task("custom", task),
            base_url=config.base_url,
            vision_image_detail=ocr_image_detail,
            response_format_type=custom_response_format_type,
        )
    raise error_factory(f"Unsupported LLM provider: {config.provider}")
