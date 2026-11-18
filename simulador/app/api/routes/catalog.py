"""Escenarios disponibles y estado de los sistemas A y B."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_manager
from app.core.config import Settings, get_settings
from app.infra.target_client import TargetClient
from app.runs.manager import RunManager

router = APIRouter(prefix="/api", tags=["simulador"])


@router.get("/scenarios")
async def list_scenarios(manager: RunManager = Depends(get_manager), settings: Settings = Depends(get_settings)) -> list[dict]:
    return await asyncio.to_thread(lambda: [s.describe(settings) for s in manager.scenarios.values()])


@router.get("/targets")
async def targets(settings: Settings = Depends(get_settings)) -> dict:
    """Salud y estadísticas de cada sistema (para las tarjetas de estado)."""

    async def one(system: str) -> dict:
        client = TargetClient(system, settings.target_url(system))
        health = await client.health()
        stats = None
        if health.get("online"):
            try:
                stats = await client.stats()
            except Exception:  # noqa: BLE001 - admin deshabilitado o error puntual
                stats = None
        return {"system": system, "url": client.base_url, "public_url": settings.public_url(system),
                "health": health, "stats": stats}

    a, b = await asyncio.gather(one("A"), one("B"))
    return {"A": a, "B": b}


@router.post("/targets/{system}/reset")
async def reset_target(system: str, settings: Settings = Depends(get_settings),
                       manager: RunManager = Depends(get_manager)) -> dict:
    if system not in ("A", "B"):
        raise HTTPException(404, "Sistema desconocido")
    if manager.active:
        raise HTTPException(409, "No se puede reiniciar mientras corre una simulación")
    return await TargetClient(system, settings.target_url(system)).reset()
