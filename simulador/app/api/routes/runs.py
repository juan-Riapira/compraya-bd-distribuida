"""Iniciar, consultar, cancelar y seguir en vivo las corridas del simulador."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_broadcaster, get_manager
from app.runs.broadcaster import Broadcaster
from app.runs.manager import BusyError, RunManager
from app.runs.models import Run
from app.scenarios.base import ScenarioError

router = APIRouter(prefix="/api/runs", tags=["corridas"])


class StartRun(BaseModel):
    scenario: str
    systems: list[str] = ["A", "B"]
    params: dict = {}


@router.post("", response_model=Run, status_code=201)
async def start_run(body: StartRun, manager: RunManager = Depends(get_manager)) -> Run:
    try:
        return await manager.start(body.scenario, body.systems, body.params)
    except BusyError as exc:
        raise HTTPException(409, str(exc)) from None
    except ScenarioError as exc:
        raise HTTPException(422, str(exc)) from None


@router.get("")
async def list_runs(manager: RunManager = Depends(get_manager)) -> dict:
    def brief(run: Run) -> dict:
        return {
            "id": run.id, "scenario": run.scenario, "systems": run.systems, "status": run.status,
            "created_at": run.created_at, "params": run.params,
            "summary": {s: {**r.summary, **r.extra, "consistent": (r.consistency or {}).get("consistent")}
                        for s, r in run.results.items()},
        }

    active = manager.active
    return {"active": active.id if active else None, "runs": [brief(r) for r in manager.history()]}


@router.get("/{run_id}", response_model=Run)
async def get_run(run_id: str, manager: RunManager = Depends(get_manager)) -> Run:
    run = manager.get(run_id)
    if run is None:
        raise HTTPException(404, "Corrida no encontrada")
    return run


@router.post("/{run_id}/cancel")
async def cancel_run(run_id: str, manager: RunManager = Depends(get_manager)) -> dict:
    if not manager.cancel(run_id):
        raise HTTPException(409, "Esa corrida no está en curso")
    return {"status": "cancelling"}


@router.delete("/{run_id}")
async def delete_run(run_id: str, manager: RunManager = Depends(get_manager)) -> dict:
    if not manager.delete(run_id):
        raise HTTPException(404, "No se pudo borrar (no existe o está en curso)")
    return {"status": "deleted"}


@router.get("/{run_id}/stream")
async def stream(run_id: str, request: Request, broadcaster: Broadcaster = Depends(get_broadcaster),
                 manager: RunManager = Depends(get_manager)) -> StreamingResponse:
    """Server-Sent Events: tick (métricas por segundo), event, result, status."""
    if manager.get(run_id) is None:
        raise HTTPException(404, "Corrida no encontrada")
    queue = broadcaster.subscribe(run_id)

    async def events():
        try:
            yield "retry: 2000\n\n"
            while not await request.is_disconnected():
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield ": ping\n\n"  # mantiene viva la conexión
        finally:
            broadcaster.unsubscribe(run_id, queue)

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
