from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from zapis.api.routes.documents import router as documents_router
from zapis.api.routes.health import router as health_router
from zapis.api.routes.ui import router as ui_router
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
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.include_router(ui_router)
    app.include_router(documents_router)
    app.include_router(health_router)
    return app


app = create_app()
