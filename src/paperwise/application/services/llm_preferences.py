from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SUPPORTED_LLM_PROVIDERS = {"openai", "gemini", "custom"}
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_OPENAI_TEXT_MODEL = "gpt-4.1-mini"
DEFAULT_OPENAI_OCR_MODEL = "gpt-4.1-nano"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
LLM_TASK_METADATA = "metadata"
LLM_TASK_GROUNDED_QA = "grounded_qa"
LLM_TASK_OCR = "ocr"


@dataclass(frozen=True)
class LLMConnectionConfig:
    id: str
    name: str
    provider: str
    base_url: str
    api_key: str
    default_model: str


@dataclass(frozen=True)
class ResolvedLLMTaskConfig:
    provider: str
    model: str
    base_url: str
    api_key: str


def normalize_llm_provider(value: Any) -> str:
    provider = str(value or "").strip().lower()
    if provider in SUPPORTED_LLM_PROVIDERS:
        return provider
    return ""


def validate_api_key_for_provider(provider: str, api_key: Any) -> str:
    normalized_provider = normalize_llm_provider(provider)
    normalized_api_key = str(api_key or "").strip()
    if not normalized_api_key:
        return ""
    if normalized_provider == "gemini" and normalized_api_key.startswith("sk-"):
        return "Gemini API keys should not start with sk-. Paste your Google AI Studio API key."
    return ""


def default_base_url_for_provider(provider: str) -> str:
    if provider == "openai":
        return DEFAULT_OPENAI_BASE_URL
    if provider == "gemini":
        return DEFAULT_GEMINI_BASE_URL
    return ""


def default_model_for_task(provider: str, task: str) -> str:
    if provider == "openai":
        if task == LLM_TASK_OCR:
            return DEFAULT_OPENAI_OCR_MODEL
        return DEFAULT_OPENAI_TEXT_MODEL
    if provider == "gemini":
        return DEFAULT_GEMINI_MODEL
    if provider == "custom":
        if task == LLM_TASK_OCR:
            return DEFAULT_OPENAI_OCR_MODEL
        return DEFAULT_OPENAI_TEXT_MODEL
    return ""


def llm_provider_defaults_payload() -> dict[str, dict[str, str]]:
    return {
        "openai": {
            "model": default_model_for_task("openai", LLM_TASK_METADATA),
            "base_url": default_base_url_for_provider("openai"),
        },
        "gemini": {
            "model": default_model_for_task("gemini", LLM_TASK_METADATA),
            "base_url": default_base_url_for_provider("gemini"),
        },
    }


def ocr_llm_provider_defaults_payload() -> dict[str, dict[str, str]]:
    return {
        "openai": {
            "model": default_model_for_task("openai", LLM_TASK_OCR),
            "base_url": default_base_url_for_provider("openai"),
        },
        "gemini": {
            "model": default_model_for_task("gemini", LLM_TASK_OCR),
            "base_url": default_base_url_for_provider("gemini"),
        },
    }


def normalize_connection_name(provider: str, fallback: str) -> str:
    if provider == "openai":
        return "OpenAI"
    if provider == "gemini":
        return "Gemini"
    if provider == "custom":
        return "Custom"
    return fallback


def _normalize_connection(raw: Any, index: int) -> LLMConnectionConfig | None:
    if not isinstance(raw, dict):
        return None
    provider = normalize_llm_provider(raw.get("provider"))
    base_url = str(raw.get("base_url") or "").strip()
    api_key = str(raw.get("api_key") or "").strip()
    default_model = str(raw.get("default_model") or "").strip()
    name = str(raw.get("name") or "").strip()
    if not provider and not base_url and not api_key and not default_model and not name:
        return None
    connection_id = str(raw.get("id") or f"connection-{index + 1}").strip() or f"connection-{index + 1}"
    return LLMConnectionConfig(
        id=connection_id,
        name=name or normalize_connection_name(provider, f"Connection {index + 1}"),
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        default_model=default_model,
    )


def _normalize_task_route(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    return {
        "connection_id": str(raw.get("connection_id") or "").strip(),
        "model": str(raw.get("model") or "").strip(),
    }


def _normalize_ocr_route(raw: Any) -> dict[str, Any]:
    normalized = _normalize_task_route(raw)
    engine = str((raw or {}).get("engine") or "llm").strip().lower() if isinstance(raw, dict) else "llm"
    if engine not in {"llm", "tesseract"}:
        engine = "llm"
    normalized["engine"] = engine
    return normalized


def _build_legacy_connection(
    *,
    provider: Any,
    base_url: Any,
    api_key: Any,
    default_model: Any,
    connection_id: str,
    name: str,
) -> LLMConnectionConfig | None:
    normalized_provider = normalize_llm_provider(provider)
    normalized_base_url = str(base_url or "").strip()
    normalized_api_key = str(api_key or "").strip()
    normalized_default_model = str(default_model or "").strip()
    if not normalized_provider and not normalized_base_url and not normalized_api_key and not normalized_default_model:
        return None
    return LLMConnectionConfig(
        id=connection_id,
        name=name,
        provider=normalized_provider,
        base_url=normalized_base_url,
        api_key=normalized_api_key,
        default_model=normalized_default_model,
    )


def _connections_equal(left: LLMConnectionConfig, right: LLMConnectionConfig) -> bool:
    return (
        left.provider == right.provider
        and left.base_url == right.base_url
        and left.api_key == right.api_key
    )


def _migrate_legacy_preferences(preferences: dict[str, Any]) -> tuple[list[LLMConnectionConfig], dict[str, Any]]:
    primary = _build_legacy_connection(
        provider=preferences.get("llm_provider"),
        base_url=preferences.get("llm_base_url"),
        api_key=preferences.get("llm_api_key"),
        default_model=preferences.get("llm_model"),
        connection_id="default-connection",
        name="Primary Connection",
    )
    connections: list[LLMConnectionConfig] = [primary] if primary is not None else []
    routing: dict[str, Any] = {
        "metadata": {
            "connection_id": primary.id if primary is not None else "",
            "model": str(preferences.get("llm_model") or "").strip(),
        },
        "grounded_qa": {
            "connection_id": primary.id if primary is not None else "",
            "model": str(preferences.get("llm_model") or "").strip(),
        },
        "ocr": {
            "engine": "llm",
            "connection_id": primary.id if primary is not None else "",
            "model": str(preferences.get("llm_model") or "").strip(),
        },
    }

    legacy_ocr_provider = str(preferences.get("ocr_provider", "llm")).strip().lower()
    if legacy_ocr_provider == "tesseract":
        routing["ocr"]["engine"] = "tesseract"
    elif legacy_ocr_provider == "llm_separate":
        ocr_connection = _build_legacy_connection(
            provider=preferences.get("ocr_llm_provider"),
            base_url=preferences.get("ocr_llm_base_url"),
            api_key=preferences.get("ocr_llm_api_key"),
            default_model=preferences.get("ocr_llm_model"),
            connection_id="ocr-connection",
            name="OCR Connection",
        )
        if ocr_connection is not None:
            if primary is None or not _connections_equal(primary, ocr_connection):
                connections.append(ocr_connection)
                ocr_connection_id = ocr_connection.id
            else:
                ocr_connection_id = primary.id
            routing["ocr"] = {
                "engine": "llm",
                "connection_id": ocr_connection_id,
                "model": str(preferences.get("ocr_llm_model") or "").strip(),
            }
    return connections, routing


def get_normalized_llm_preferences(preferences: dict[str, Any]) -> dict[str, Any]:
    raw_connections = preferences.get("llm_connections")
    raw_routing = preferences.get("llm_routing")
    if isinstance(raw_connections, list) and isinstance(raw_routing, dict):
        connections = [
            connection
            for index, raw in enumerate(raw_connections)
            if (connection := _normalize_connection(raw, index)) is not None
        ]
        routing = {
            "metadata": _normalize_task_route(raw_routing.get("metadata")),
            "grounded_qa": _normalize_task_route(raw_routing.get("grounded_qa")),
            "ocr": _normalize_ocr_route(raw_routing.get("ocr")),
        }
    else:
        connections, routing = _migrate_legacy_preferences(preferences)

    if connections:
        connection_ids = {connection.id for connection in connections}
        for task_name in ("metadata", "grounded_qa", "ocr"):
            task_route = routing[task_name]
            if task_route["connection_id"] and task_route["connection_id"] not in connection_ids:
                task_route["connection_id"] = connections[0].id
    else:
        for task_name in ("metadata", "grounded_qa", "ocr"):
            routing[task_name]["connection_id"] = ""

    return {
        "llm_connections": [
            {
                "id": connection.id,
                "name": connection.name,
                "provider": connection.provider,
                "base_url": connection.base_url,
                "api_key": connection.api_key,
                "default_model": connection.default_model,
            }
            for connection in connections
        ],
        "llm_routing": routing,
    }


def resolve_task_config(preferences: dict[str, Any], task: str) -> ResolvedLLMTaskConfig | None:
    normalized = get_normalized_llm_preferences(preferences)
    connections = {
        raw["id"]: LLMConnectionConfig(
            id=str(raw["id"]),
            name=str(raw["name"]),
            provider=str(raw["provider"]),
            base_url=str(raw["base_url"]),
            api_key=str(raw["api_key"]),
            default_model=str(raw.get("default_model", "")),
        )
        for raw in normalized["llm_connections"]
    }
    routing = normalized["llm_routing"]

    if task == LLM_TASK_OCR:
        ocr_route = routing["ocr"]
        if ocr_route["engine"] == "tesseract":
            return None
        route = ocr_route
    elif task == LLM_TASK_METADATA:
        route = routing["metadata"]
    elif task == LLM_TASK_GROUNDED_QA:
        route = routing["grounded_qa"]
    else:
        return None

    connection_id = str(route.get("connection_id") or "").strip()
    connection = connections.get(connection_id)
    if connection is None:
        return None
    model = (
        str(route.get("model") or "").strip()
        or connection.default_model
        or default_model_for_task(connection.provider, task)
    )
    return ResolvedLLMTaskConfig(
        provider=connection.provider,
        model=model,
        base_url=connection.base_url or default_base_url_for_provider(connection.provider),
        api_key=connection.api_key,
    )
