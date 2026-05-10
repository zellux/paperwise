from paperwise.application.interfaces import PreferenceRepository
from paperwise.application.services.llm_preferences import resolve_ocr_auto_switch, resolve_ocr_provider
from paperwise.application.services.user_preferences import load_user_preferences


def resolve_owner_ocr_provider(repository: PreferenceRepository, owner_id: str) -> str:
    return resolve_ocr_provider(load_user_preferences(repository=repository, user_id=owner_id))


def resolve_owner_ocr_auto_switch(repository: PreferenceRepository, owner_id: str) -> bool:
    return resolve_ocr_auto_switch(load_user_preferences(repository=repository, user_id=owner_id))
