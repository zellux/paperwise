from dataclasses import dataclass
from typing import Any

import httpx

from paperwise.application.interfaces import LLMProvider
from paperwise.application.services.llm_preferences import (
    LLM_TASK_GROUNDED_QA,
    LLM_TASK_METADATA,
    LLM_TASK_OCR,
    get_normalized_llm_preferences,
)
from paperwise.application.services.llm_provider_factory import resolve_llm_provider_from_preferences

OCR_CONNECTION_TEST_IMAGE_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAANwAAABGCAIAAAAoxW3zAAABFElEQVR42u3cyQ2EMBAAQeefNKQAwnOZ6u/"
    "iBUbFAyF5XVKzlhEISglKQSlBKSglKAWlBKUEpaCUoBSUEpSCUoJSUEpHoFxvSlsbOKaW9xu3Nm50"
    "jw6GEkoooYQSSiihhBLKFig3/hp33uJBB9xv1V99eYDz3r6hhBJKKKGEEkoooYQSSihbzApKKKGEE"
    "koooYQSSiihTPxWthHlxrVpz0b2rKCEEkoooYQSSiihhPLXKI9/+x5xGVBCCSWUUEIJJZRQQgkllF"
    "BCCSWUUEIJJZRQQgnlDJRVuz5MRFm1y8Wk3USghBJKKKGEEkoooYSyBqUUyNoIBKUEpaCUoBSUEpSC"
    "UoJSglJQSlAKSglKQSlBqZ93AzSzyIKXc69aAAAAAElFTkSuQmCC"
)
OCR_CONNECTION_TEST_EXPECTED_WORDS = ("ocr", "test")
OCR_CONNECTION_TEST_EXPECTED_DIGITS = "12"


class LLMConnectionConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMConnectionTestInput:
    task: str | None = None
    connection_name: str | None = None
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


@dataclass(frozen=True)
class LLMConnectionTestResult:
    provider: str
    model: str


def run_llm_connection_test(
    *,
    preferences: dict[str, Any],
    payload: LLMConnectionTestInput,
    provider_override: LLMProvider | None,
) -> LLMConnectionTestResult:
    merged_preferences = _merge_llm_preferences(preferences, payload)
    requested_task = str(payload.task or "").strip().lower()
    task_specific_probe = requested_task in {LLM_TASK_METADATA, LLM_TASK_GROUNDED_QA, LLM_TASK_OCR}
    task = _normalize_llm_connection_test_task(payload.task)
    missing_provider_detail, missing_api_key_detail, missing_base_url_detail = _llm_connection_test_missing_details(task)
    llm_provider = resolve_llm_provider_from_preferences(
        preferences=merged_preferences,
        provider_override=provider_override,
        task=task,
        missing_provider_detail=missing_provider_detail,
        missing_api_key_detail=missing_api_key_detail,
        missing_base_url_detail=missing_base_url_detail,
        custom_response_format_type="text",
        error_factory=LLMConnectionConfigError,
    )
    normalized_llm = get_normalized_llm_preferences(merged_preferences)
    task_route = normalized_llm["llm_routing"][task]
    connections_by_id = {
        str(connection["id"]): connection for connection in normalized_llm["llm_connections"]
    }
    selected_connection = connections_by_id.get(str(task_route.get("connection_id", "")), {})
    provider_name = str(selected_connection.get("provider", "")).strip().lower() or "custom"
    model_name = str(task_route.get("model", "")).strip() or "default"
    if provider_name == "custom" and not task_specific_probe:
        _test_custom_llm_connection(
            base_url=str(selected_connection.get("base_url", "")).strip(),
            api_key=str(selected_connection.get("api_key", "")).strip(),
            model=model_name,
        )
    else:
        _run_llm_connection_task_test(llm_provider, task)
    return LLMConnectionTestResult(provider=provider_name, model=model_name)


def format_llm_connection_test_error(exc: Exception) -> str:
    message = str(exc)
    response = getattr(exc, "response", None)
    if response is None:
        return message

    response_text = str(getattr(response, "text", "") or "").strip()
    if not response_text:
        return message

    status_code = getattr(response, "status_code", None)
    prefix = f"HTTP {status_code} response" if status_code else "Provider response"
    if response_text in message:
        return message
    return f"{message}; {prefix}: {response_text}"


def _merge_llm_preferences(
    preferences: dict[str, Any],
    payload: LLMConnectionTestInput,
) -> dict[str, Any]:
    merged = dict(preferences)
    normalized = get_normalized_llm_preferences(merged)
    connection = {
        "id": "test-connection",
        "name": payload.connection_name or "Connection Test",
        "provider": str(payload.provider or "").strip(),
        "base_url": str(payload.base_url or "").strip(),
        "api_key": str(payload.api_key or "").strip(),
    }
    normalized["llm_connections"] = [connection]
    normalized["llm_routing"]["metadata"] = {
        "connection_id": "test-connection",
        "model": str(payload.model or "").strip(),
    }
    normalized["llm_routing"]["grounded_qa"] = {
        "connection_id": "test-connection",
        "model": str(payload.model or "").strip(),
    }
    normalized["llm_routing"]["ocr"] = {
        "engine": "llm",
        "connection_id": "test-connection",
        "model": str(payload.model or "").strip(),
    }
    merged.update(normalized)
    return merged


def _test_custom_llm_connection(*, base_url: str, api_key: str, model: str) -> None:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=10.0, headers=headers) as client:
        response = client.get("/models")
        response.raise_for_status()
        payload = response.json()

    if not model or model == "default":
        return
    model_ids = {
        str(item.get("id", "")).strip()
        for item in payload.get("data", [])
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }
    if model_ids and model not in model_ids:
        available = ", ".join(sorted(model_ids)[:10])
        suffix = f" Available models: {available}." if available else ""
        raise RuntimeError(f"Model '{model}' was not found in the provider's /models response.{suffix}")


def _normalize_llm_connection_test_task(value: str | None) -> str:
    task = str(value or "").strip().lower()
    if task in {LLM_TASK_METADATA, LLM_TASK_GROUNDED_QA, LLM_TASK_OCR}:
        return task
    return LLM_TASK_METADATA


def _llm_connection_test_missing_details(task: str) -> tuple[str, str, str]:
    if task == LLM_TASK_GROUNDED_QA:
        return (
            "Configure a Grounded Q&A LLM connection in Settings before testing Ask Your Docs.",
            "Selected Grounded Q&A LLM connection requires an API key in Settings.",
            "Custom Grounded Q&A connection requires a base URL in Settings.",
        )
    if task == LLM_TASK_OCR:
        return (
            "Configure an OCR LLM connection in Settings before testing OCR.",
            "Selected OCR LLM connection requires an API key in Settings.",
            "Custom OCR LLM connection requires a base URL in Settings.",
        )
    return (
        "Configure an LLM provider in Settings before running LLM parse.",
        "Selected LLM provider requires your API key in Settings.",
        "Custom LLM provider requires a base URL in Settings.",
    )


def _test_llm_vision_ocr_connection(llm_provider: LLMProvider) -> None:
    image_ocr = getattr(llm_provider, "extract_ocr_text_from_images", None)
    if not callable(image_ocr):
        raise RuntimeError("Selected OCR provider does not support image OCR.")

    result = image_ocr(
        filename="ocr-connection-test.png",
        image_data_urls=[OCR_CONNECTION_TEST_IMAGE_DATA_URL],
    )
    normalized_result = " ".join(str(result or "").lower().split())
    if not normalized_result:
        raise RuntimeError("OCR model returned empty text for the connection test image.")
    compact_result = "".join(character for character in normalized_result if character.isalnum())
    missing_words = [
        word for word in OCR_CONNECTION_TEST_EXPECTED_WORDS if word not in normalized_result
    ]
    if missing_words or OCR_CONNECTION_TEST_EXPECTED_DIGITS not in compact_result:
        raise RuntimeError(
            "OCR model did not read the connection test image. "
            "Expected OCR text to include OCR TEST and at least part of 123. "
            f"Received: {str(result or '').strip()[:200]}"
        )


def _run_llm_connection_task_test(llm_provider: LLMProvider, task: str) -> None:
    if task == LLM_TASK_GROUNDED_QA:
        answer_with_tools = getattr(llm_provider, "answer_with_tools", None)
        if not callable(answer_with_tools):
            raise RuntimeError("Selected Grounded Q&A provider does not support conversational tool use.")
        answer_with_tools(
            messages=[
                {
                    "role": "system",
                    "content": "You are Paperwise's model configuration tester.",
                },
                {
                    "role": "user",
                    "content": "Reply with a brief confirmation that the Paperwise Ask Your Docs model config test is working.",
                },
            ],
            tools=[],
        )
        return
    if task == LLM_TASK_OCR:
        _test_llm_vision_ocr_connection(llm_provider)
        return
    llm_provider.suggest_metadata(
        filename="connection-test.txt",
        text_preview="Connection test sample.",
        current_correspondent=None,
        current_document_type=None,
        existing_correspondents=[],
        existing_document_types=[],
        existing_tags=["Test"],
    )
