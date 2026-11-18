"""Punto de entrada del Sistema B: crea y configura la aplicación FastAPI."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.api.routes import admin, health, redis_panel
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.db.indexes import ensure_indexes
from app.db.mongo import MongoConnection
from app.db.redis import RedisConnection

WEB_DIR = Path(__file__).parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.mongo = MongoConnection(settings)
    app.state.redis = RedisConnection(settings)
    await ensure_indexes(app.state.mongo.db)
    yield
    await app.state.redis.close()
    await app.state.mongo.close()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name, version="1.1.0", lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_prefix)
    if settings.admin_enabled:
        app.include_router(admin.router)
        app.include_router(redis_panel.router)
    # La tienda web (HTML/CSS/JS) se sirve en "/"; se monta al final para no tapar la API.
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app


app = create_app()
