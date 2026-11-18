"""Escenario 3 · Caída de un nodo: se apaga un nodo de base de datos con tráfico activo.

A: se apaga el único PostgreSQL.  B: se apaga el primario del shard NORTE.
Se mide cuántos segundos la tienda no pudo vender y si se recupera sola.
"""
from app.engine.load_runner import run_load
from app.scenarios.base import Param, Scenario, ScenarioError, finish_system, prepare_system


class FailoverScenario(Scenario):
    key = "failover"
    title = "Caída de un nodo"
    summary = "Con compradores activos se apaga un nodo de base de datos: ¿la tienda sigue vendiendo?"
    params = (
        Param("users", "Compradores simultáneos", 60, 5, 300),
        Param("duration_s", "Duración por sistema (s)", 60, 20, 300),
        Param("kill_at_s", "Apagar el nodo en el segundo", 15, 3, 200),
        Param("restore_at_s", "Encender el nodo en el segundo", 45, 5, 290, "Simula la reparación manual"),
        Param("reset", "Reiniciar datos antes", True, kind="bool"),
    )

    def availability(self, settings):
        from app.infra.chaos import build_injector

        return {s: build_injector(s, settings).available for s in ("A", "B")}

    def extra_validation(self, params, settings):
        if not params["kill_at_s"] < params["restore_at_s"] < params["duration_s"]:
            raise ScenarioError("Debe cumplirse: apagar < encender < duración")
        return params

    async def run(self, ctx) -> None:
        p = ctx.params
        for system in ctx.run.systems:
            injector = ctx.injector(system)
            if not injector.available:
                await ctx.event("error", f"No hay cómo apagar un nodo del Sistema {system} ({injector.description}). "
                                         "Revisa la configuración FAILOVER_* del simulador.", system)
                continue
            if ctx.cancel.is_set() or not await prepare_system(ctx, system):
                continue
            await ctx.event("phase", f"Tráfico con {p['users']} compradores; el nodo cae en t={p['kill_at_s']} s", system)

            async def on_tick(data, system=system):
                await ctx.tick(system, data)

            async def chaos(metrics, system=system, injector=injector):
                if not await ctx.sleep(p["kill_at_s"]):
                    return
                await ctx.event("kill", await injector.kill(), system, metrics.elapsed())
                restored = False
                try:
                    if await ctx.sleep(p["restore_at_s"] - p["kill_at_s"]):
                        await ctx.event("restore", await injector.restore(), system, metrics.elapsed())
                        restored = True
                finally:
                    if not restored:  # cancelación: nunca dejar el nodo apagado
                        await injector.restore()

            metrics = await run_load(
                base_url=ctx.settings.target_url(system),
                users=p["users"],
                duration_s=p["duration_s"],
                ramp_up_s=2,
                think_time_s=(0.1, 0.4),
                timeout_s=5,
                on_tick=on_tick,
                cancel=ctx.cancel,
                during=chaos,
            )
            result = ctx.result(system)
            result.summary = metrics.summary()
            window = [t for t in result.timeline if p["kill_at_s"] <= t["t"] < p["restore_at_s"]]
            down_any = [t for t in window if t["ok"] == 0]
            down_sales = [t for t in window if t["checkouts"] == 0]
            # Recuperación = primer segundo con ventas DESPUÉS de haber dejado de vender.
            first_down = next((t["t"] for t in window if t["checkouts"] == 0), None)
            recovered = None if first_down is None else next(
                (t["t"] for t in window if t["t"] > first_down and t["checkouts"] > 0), None)
            if first_down is None:
                recovered = p["kill_at_s"]  # nunca dejó de vender
            result.extra = {
                "outage_window_s": p["restore_at_s"] - p["kill_at_s"],
                "seconds_without_any_response": len(down_any),
                "seconds_without_sales": len(down_sales),
                "self_recovered": recovered is not None,
                "recovered_after_s": (recovered - p["kill_at_s"]) if recovered is not None else None,
            }
            await finish_system(ctx, system, settle_s=8)
