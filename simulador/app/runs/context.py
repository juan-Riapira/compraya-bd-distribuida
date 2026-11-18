"""Contexto que recibe cada escenario: le da todo lo que necesita sin acoplarlo
a la API web ni al almacenamiento (publicar avances, guardar resultados, etc.)."""
import asyncio

from app.core.config import Settings
from app.infra.chaos import FailureInjector, build_injector
from app.infra.target_client import TargetClient
from app.runs.broadcaster import Broadcaster
from app.runs.models import Run, RunEvent, SystemResult


class RunContext:
    def __init__(self, run: Run, settings: Settings, broadcaster: Broadcaster):
        self.run = run
        self.settings = settings
        self.cancel = asyncio.Event()
        self._broadcaster = broadcaster

    # --- recursos ---
    def target(self, system: str) -> TargetClient:
        return TargetClient(system, self.settings.target_url(system))

    def injector(self, system: str) -> FailureInjector:
        return build_injector(system, self.settings)

    @property
    def params(self) -> dict:
        return self.run.params

    # --- publicación en vivo ---
    async def event(self, kind: str, message: str, system: str | None = None, t: float | None = None) -> None:
        ev = RunEvent(kind=kind, message=message, system=system, t=round(t, 1) if t is not None else None)
        self.run.events.append(ev)
        await self._broadcaster.publish(self.run.id, "event", ev.model_dump())

    async def tick(self, system: str, data: dict) -> None:
        self.result(system).timeline.append(data)
        await self._broadcaster.publish(self.run.id, "tick", {"system": system, **data})

    def result(self, system: str) -> SystemResult:
        if system not in self.run.results:
            self.run.results[system] = SystemResult(system=system)
        return self.run.results[system]

    async def publish_result(self, system: str) -> None:
        data = self.result(system).model_dump(exclude={"timeline"})
        await self._broadcaster.publish(self.run.id, "result", data)

    async def sleep(self, seconds: float) -> bool:
        """Espera respetando la cancelación. Devuelve False si se canceló."""
        try:
            await asyncio.wait_for(self.cancel.wait(), timeout=seconds)
            return False
        except TimeoutError:
            return True
