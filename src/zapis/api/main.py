from fastapi import FastAPI

from zapis.api.routes.health import router as health_router
from zapis.infrastructure.config import get_settings
from zapis.infrastructure.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="zapis API",
        version="0.1.0",
        description="AI-native document management platform API",
    )
    app.include_router(health_router)
    return app


app = create_app()

