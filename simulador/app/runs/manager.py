"""Orquesta las corridas: valida, ejecuta UNA a la vez en segundo plano,
publica el progreso y guarda el resultado."""
import asyncio
import logging
import uuid
from datetime import UTC, datetime

from app.core.config import Settings
from app.runs.broadcaster import Broadcaster
from app.runs.context import RunContext
from app.runs.models import Run, RunStatus
from app.runs.repository import RunRepository
from app.scenarios.base import Scenario, ScenarioError

log = logging.getLogger(__name__)


class BusyError(Exception):
    pass


class RunManager:
    def __init__(self, settings: Settings, repository: RunRepository, broadcaster: Broadcaster,
                 scenarios: dict[str, Scenario]):
        self._settings = settings
        self._repo = repository
        self._broadcaster = broadcaster
        self.scenarios = scenarios
        self._active: RunContext | None = None
        self._task: asyncio.Task | None = None

    @property
    def active(self) -> Run | None:
        return self._active.run if self._active else None

    def get(self, run_id: str) -> Run | None:
        if self._active and self._active.run.id == run_id:
            return self._active.run
        return self._repo.get(run_id)

    def history(self) -> list[Run]:
        return self._repo.list()

    def delete(self, run_id: str) -> bool:
        if self._active and self._active.run.id == run_id:
            return False
        return self._repo.delete(run_id)

    async def start(self, scenario_key: str, systems: list[str], params: dict) -> Run:
        if self._active:
            raise BusyError("Ya hay una simulación en curso. Espera a que termine o cancélala.")
        scenario = self.scenarios.get(scenario_key)
        if scenario is None:
            raise ScenarioError(f"Escenario desconocido: {scenario_key}")
        clean = scenario.validate(params, self._settings)
        systems = [s for s in ("A", "B") if s in systems]
        if not systems:
            raise ScenarioError("Elige al menos un sistema (A o B).")

        run = Run(id=datetime.now(UTC).strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4],
                  scenario=scenario_key, params=clean, systems=systems)
        self._active = RunContext(run, self._settings, self._broadcaster)
        self._task = asyncio.create_task(self._execute(scenario, self._active))
        return run

    def cancel(self, run_id: str) -> bool:
        if self._active and self._active.run.id == run_id:
            self._active.cancel.set()
            return True
        return False

    async def _execute(self, scenario: Scenario, ctx: RunContext) -> None:
        run = ctx.run
        run.status = RunStatus.RUNNING
        await self._broadcaster.publish(run.id, "status", {"status": run.status})
        try:
            await scenario.run(ctx)
            run.status = RunStatus.CANCELLED if ctx.cancel.is_set() else RunStatus.DONE
        except Exception as exc:  # noqa: BLE001 - se informa en la interfaz
            log.exception("La corrida %s falló", run.id)
            run.status = RunStatus.FAILED
            run.error = f"{type(exc).__name__}: {exc}"
            await ctx.event("error", run.error)
        finally:
            run.finished_at = datetime.now(UTC)
            self._repo.save(run)
            await self._broadcaster.publish(run.id, "status", {"status": run.status, "error": run.error})
            self._active = None
