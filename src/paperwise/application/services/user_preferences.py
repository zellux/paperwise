from typing import Any

from paperwise.application.interfaces import PreferenceRepository
from paperwise.application.services.llm_preferences import get_normalized_llm_preferences


def load_user_preferences(
    *,
    repository: PreferenceRepository,
    user_id: str,
) -> dict[str, Any]:
    preference = repository.get_user_preference(user_id)
    return dict(preference.preferences) if preference is not None else {}


def normalized_user_preferences(preferences: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(preferences)
    normalized.update(get_normalized_llm_preferences(normalized))
    return normalized


def load_normalized_user_preferences(
    *,
    repository: PreferenceRepository,
    user_id: str,
) -> dict[str, Any]:
    return normalized_user_preferences(load_user_preferences(repository=repository, user_id=user_id))
