import pytest

from paperwise.application.services.llm_preferences import (
    resolve_ocr_auto_switch,
    resolve_ocr_provider,
)
from paperwise.application.services.llm_provider_factory import resolve_llm_provider_from_preferences


class FakeLLMProvider:
    pass


def test_resolve_llm_provider_uses_explicit_override() -> None:
    provider = FakeLLMProvider()

    resolved = resolve_llm_provider_from_preferences(
        preferences={},
        provider_override=provider,
    )

    assert resolved is provider


def test_resolve_llm_provider_requires_configuration_without_override() -> None:
    with pytest.raises(RuntimeError, match="Configure an LLM provider"):
        resolve_llm_provider_from_preferences(
            preferences={},
            provider_override=None,
        )


def test_resolve_ocr_provider_prefers_modern_routing() -> None:
    preferences = {
        "ocr_provider": "tesseract",
        "llm_connections": [
            {
                "id": "primary",
                "name": "Primary",
                "provider": "openai",
                "api_key": "sk-test",
            }
        ],
        "llm_routing": {
            "metadata": {"connection_id": "primary"},
            "grounded_qa": {"connection_id": "primary"},
            "ocr": {"engine": "llm", "connection_id": "primary"},
        },
    }

    assert resolve_ocr_provider(preferences) == "llm_separate"


def test_resolve_ocr_provider_supports_legacy_values() -> None:
    assert resolve_ocr_provider({"ocr_provider": "tesseract"}) == "tesseract"
    assert resolve_ocr_provider({"ocr_provider": "llm_separate"}) == "llm_separate"
    assert resolve_ocr_provider({"ocr_provider": "unknown"}) == "llm"


def test_resolve_ocr_auto_switch_normalizes_values() -> None:
    assert resolve_ocr_auto_switch({"ocr_auto_switch": True}) is True
    assert resolve_ocr_auto_switch({"ocr_auto_switch": "yes"}) is True
    assert resolve_ocr_auto_switch({"ocr_auto_switch": "no"}) is False
