"""Rutas de administración (las usa el simulador). Se desactivan con ADMIN_ENABLED=false."""
from fastapi import APIRouter, Depends

from app.api.deps import get_admin_service
from app.schemas.admin import ConsistencyOut, StatsOut
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["administración"])


@router.post("/reset")
async def reset(service: AdminService = Depends(get_admin_service)) -> dict:
    """Borra todo y vuelve a cargar el dataset inicial."""
    return {"status": "ok", **(await service.reset())}


@router.get("/stats", response_model=StatsOut)
async def stats(service: AdminService = Depends(get_admin_service)) -> StatsOut:
    return await service.stats()


@router.get("/consistency", response_model=ConsistencyOut)
async def consistency(service: AdminService = Depends(get_admin_service)) -> ConsistencyOut:
    return await service.consistency()
