import pytest

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
