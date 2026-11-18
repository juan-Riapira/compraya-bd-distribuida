"""Punto de entrada del simulador de pruebas A vs B."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import catalog, runs
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.runs.broadcaster import Broadcaster
from app.runs.manager import RunManager
from app.runs.repository import RunRepository
from app.scenarios import all_scenarios

WEB_DIR = Path(__file__).parent / "web"


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="CompraYa · Simulador de pruebas A vs B", version="1.0.0")
    app.state.broadcaster = Broadcaster()
    app.state.manager = RunManager(
        settings=settings,
        repository=RunRepository(settings.data_dir / "runs"),
        broadcaster=app.state.broadcaster,
        scenarios=all_scenarios(),
    )
    app.include_router(catalog.router)
    app.include_router(runs.router)
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
    return app


app = create_app()
