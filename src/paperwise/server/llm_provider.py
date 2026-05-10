from typing import Any

from fastapi import HTTPException, status

from paperwise.application.interfaces import LLMProvider, PreferenceRepository
from paperwise.application.services.llm_preferences import LLM_TASK_METADATA, LLM_TASK_OCR
from paperwise.application.services.llm_provider_factory import resolve_llm_provider_from_preferences
from paperwise.application.services.user_preferences import load_user_preferences


def resolve_http_llm_provider_from_preferences(
    *,
    preferences: dict[str, Any],
    provider_override: LLMProvider | None = None,
    task: str = LLM_TASK_METADATA,
    missing_provider_detail: str = "Configure an LLM provider in Settings before running LLM parse.",
    missing_api_key_detail: str = "Selected LLM provider requires your API key in Settings.",
    missing_base_url_detail: str = "Custom LLM provider requires a base URL in Settings.",
) -> LLMProvider:
    return resolve_llm_provider_from_preferences(
        preferences=preferences,
        provider_override=provider_override,
        task=task,
        missing_provider_detail=missing_provider_detail,
        missing_api_key_detail=missing_api_key_detail,
        missing_base_url_detail=missing_base_url_detail,
        custom_response_format_type="text",
        error_factory=lambda detail: HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ),
    )


def resolve_http_llm_provider_for_user(
    *,
    repository: PreferenceRepository,
    user_id: str,
    provider_override: LLMProvider | None = None,
    task: str = LLM_TASK_METADATA,
    missing_provider_detail: str = "Configure an LLM provider in Settings before running LLM parse.",
    missing_api_key_detail: str = "Selected LLM provider requires your API key in Settings.",
    missing_base_url_detail: str = "Custom LLM provider requires a base URL in Settings.",
) -> LLMProvider:
    return resolve_http_llm_provider_from_preferences(
        preferences=load_user_preferences(repository=repository, user_id=user_id),
        provider_override=provider_override,
        task=task,
        missing_provider_detail=missing_provider_detail,
        missing_api_key_detail=missing_api_key_detail,
        missing_base_url_detail=missing_base_url_detail,
    )


def resolve_http_metadata_llm_provider_for_user(
    *,
    repository: PreferenceRepository,
    user_id: str,
    provider_override: LLMProvider | None = None,
) -> LLMProvider:
    return resolve_http_llm_provider_for_user(
        repository=repository,
        user_id=user_id,
        provider_override=provider_override,
        task=LLM_TASK_METADATA,
    )


def resolve_http_ocr_llm_provider_for_user(
    *,
    repository: PreferenceRepository,
    user_id: str,
    provider_override: LLMProvider | None = None,
) -> LLMProvider:
    return resolve_http_llm_provider_for_user(
        repository=repository,
        user_id=user_id,
        provider_override=provider_override,
        task=LLM_TASK_OCR,
        missing_provider_detail="Configure an OCR LLM connection in Settings before OCR parsing.",
        missing_api_key_detail="Selected OCR LLM connection requires an API key in Settings.",
        missing_base_url_detail="Custom OCR LLM connection requires a base URL in Settings.",
    )
