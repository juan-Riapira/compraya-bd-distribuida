"""Endpoint de salud: verifica MongoDB (vía mongos) y Redis, e identifica la réplica de la API."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings

router = APIRouter(tags=["salud"])


@router.get("/health")
async def health(request: Request, settings: Settings = Depends(get_settings)) -> JSONResponse:
    checks = {}
    for name, conn in (("mongodb", request.app.state.mongo), ("redis", request.app.state.redis)):
        try:
            await conn.ping()
            checks[name] = "ok"
        except Exception as exc:  # noqa: BLE001 - el health check debe reportar, no fallar
            checks[name] = f"error: {type(exc).__name__}"
    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ok" if healthy else "degraded", "system": "B", "instance": settings.instance_id, **checks},
    )
