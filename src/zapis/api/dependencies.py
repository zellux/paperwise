from zapis.infrastructure.config import Settings, get_settings


def settings_dependency() -> Settings:
    return get_settings()

