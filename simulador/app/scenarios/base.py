"""Contrato común de los escenarios de prueba."""
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass

from app.core.config import Settings


class ScenarioError(ValueError):
    pass


@dataclass(frozen=True)
class Param:
    name: str
    label: str
    default: int | float | bool | str
    min: float | None = None
    max: float | None = None
    help: str = ""
    kind: str = "int"   # int | float | bool | text


class Scenario(ABC):
    key: str
    title: str
    summary: str          # qué demuestra, en una frase
    params: tuple[Param, ...] = ()

    def describe(self, settings: Settings) -> dict:
        return {
            "key": self.key,
            "title": self.title,
            "summary": self.summary,
            "params": [asdict(p) for p in self.params],
            "available": self.availability(settings),
        }

    def availability(self, settings: Settings) -> dict[str, bool]:
        return {"A": True, "B": True}

    def validate(self, raw: dict, settings: Settings) -> dict:
        clean = {}
        for p in self.params:
            value = raw.get(p.name, p.default)
            try:
                if p.kind == "int":
                    value = int(value)
                elif p.kind == "float":
                    value = float(value)
                elif p.kind == "bool":
                    value = value in (True, "true", "1", 1, "on")
                else:
                    value = str(value)
            except (TypeError, ValueError):
                raise ScenarioError(f"«{p.label}» debe ser un número") from None
            if p.min is not None and value < p.min or p.max is not None and value > p.max:
                raise ScenarioError(f"«{p.label}» debe estar entre {p.min:g} y {p.max:g}")
            clean[p.name] = value
        return self.extra_validation(clean, settings)

    def extra_validation(self, params: dict, settings: Settings) -> dict:
        return params

    @abstractmethod
    async def run(self, ctx) -> None: ...


async def prepare_system(ctx, system: str) -> bool:
    """Comprueba que el sistema responde y, si se pidió, reinicia sus datos."""
    target = ctx.target(system)
    health = await target.health()
    if not health.get("online"):
        await ctx.event("error", f"El Sistema {system} no responde en {target.base_url}. Se omite.", system)
        return False
    if ctx.params.get("reset", True):
        await ctx.event("phase", "Reiniciando datos al estado inicial…", system)
        await target.reset()
    return True


async def finish_system(ctx, system: str, settle_s: float = 3) -> None:
    """Espera a que terminen las peticiones en vuelo y verifica consistencia."""
    await ctx.event("phase", "Verificando consistencia del inventario…", system)
    await ctx.sleep(settle_s)
    target = ctx.target(system)
    result = ctx.result(system)
    try:
        result.consistency = await target.consistency()
        result.stats = await target.stats()
    except Exception as exc:  # noqa: BLE001
        await ctx.event("error", f"No se pudo verificar la consistencia: {exc}", system)
    await ctx.publish_result(system)
