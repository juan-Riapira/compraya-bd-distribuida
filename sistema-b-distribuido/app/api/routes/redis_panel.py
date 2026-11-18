"""Rutas del panel de Redis (demostración). Se desactivan junto con ADMIN_ENABLED."""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_redis_inspector_service
from app.schemas.redis_panel import RedisPanelOut
from app.services.redis_inspector_service import RedisInspectorService, UnknownGroupError

router = APIRouter(prefix="/admin/redis", tags=["panel de Redis"])


@router.get("", response_model=RedisPanelOut)
async def snapshot(
    group: str = Query("product", description="product · list · stock · cart · idem"),
    limit: int = Query(40, ge=1, le=200),
    service: RedisInspectorService = Depends(get_redis_inspector_service),
) -> RedisPanelOut:
    """Llaves de un grupo con su tipo, valor y segundos de vida restantes (TTL)."""
    try:
        return await service.snapshot(group, limit)
    except UnknownGroupError as exc:
        raise HTTPException(status_code=404, detail=f"Grupo desconocido: {exc}") from exc


@router.delete("/cache")
async def clear_catalog_cache(service: RedisInspectorService = Depends(get_redis_inspector_service)) -> dict:
    """Vacía SOLO la caché del catálogo; la siguiente consulta la vuelve a llenar desde MongoDB."""
    return {"deleted": await service.clear_catalog_cache()}
