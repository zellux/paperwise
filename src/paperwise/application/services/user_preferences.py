from typing import Any

from paperwise.application.interfaces import PreferenceRepository


def load_user_preferences(
    *,
    repository: PreferenceRepository,
    user_id: str,
) -> dict[str, Any]:
    preference = repository.get_user_preference(user_id)
    return dict(preference.preferences) if preference is not None else {}
