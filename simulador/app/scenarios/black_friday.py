"""Escenario 1 · Black Friday: tráfico mixto de muchos compradores a la vez."""
from app.engine.load_runner import run_load
from app.scenarios.base import Param, Scenario, finish_system, prepare_system


class BlackFridayScenario(Scenario):
    key = "black_friday"
    title = "Black Friday"
    summary = "Muchos compradores navegan, agregan al carrito y pagan; el 80 % mira las ofertas del día."
    params = (
        Param("users", "Compradores simultáneos", 150, 10, 600, "Cada uno es un navegador abierto comprando"),
        Param("duration_s", "Duración por sistema (s)", 45, 10, 300),
        Param("ramp_up_s", "Rampa de entrada (s)", 10, 0, 120, "Tiempo en que llegan todos los compradores"),
        Param("think_min_ms", "Pausa mínima entre clics (ms)", 100, 0, 5000),
        Param("think_max_ms", "Pausa máxima entre clics (ms)", 600, 0, 10000),
        Param("reset", "Reiniciar datos antes", True, kind="bool"),
    )

    def extra_validation(self, params, settings):
        params["users"] = min(params["users"], settings.max_virtual_users)
        params["duration_s"] = min(params["duration_s"], settings.max_duration_s)
        params["think_max_ms"] = max(params["think_max_ms"], params["think_min_ms"])
        return params

    async def run(self, ctx) -> None:
        p = ctx.params
        for system in ctx.run.systems:
            if ctx.cancel.is_set() or not await prepare_system(ctx, system):
                continue
            await ctx.event("phase", f"Lanzando {p['users']} compradores durante {p['duration_s']} s…", system)

            async def on_tick(data, system=system):
                await ctx.tick(system, data)

            metrics = await run_load(
                base_url=ctx.settings.target_url(system),
                users=p["users"],
                duration_s=p["duration_s"],
                ramp_up_s=p["ramp_up_s"],
                think_time_s=(p["think_min_ms"] / 1000, p["think_max_ms"] / 1000),
                timeout_s=ctx.settings.request_timeout_s,
                on_tick=on_tick,
                cancel=ctx.cancel,
            )
            ctx.result(system).summary = metrics.summary()
            await finish_system(ctx, system)
