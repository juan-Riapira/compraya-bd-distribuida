"""Acceso a los objetos compartidos que viven en app.state."""
from fastapi import Request

from app.core.config import Settings, get_settings
from app.runs.broadcaster import Broadcaster
from app.runs.manager import RunManager


def get_manager(request: Request) -> RunManager:
    return request.app.state.manager


def get_broadcaster(request: Request) -> Broadcaster:
    return request.app.state.broadcaster


__all__ = ["get_manager", "get_broadcaster", "get_settings", "Settings"]
