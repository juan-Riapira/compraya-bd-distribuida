"""Escenario 2 · Venta relámpago: todos pagan EL MISMO producto en el mismo instante.

Aísla el efecto de la arquitectura de datos: en A las compras quedan en fila
detrás del bloqueo de la fila del producto; en B avanzan en paralelo.
"""
import asyncio
import time

from app.engine.load_runner import make_client, publish_ticks
from app.engine.metrics import MetricsCollector
from app.scenarios.base import Param, Scenario, finish_system, prepare_system


class FlashSaleScenario(Scenario):
    key = "flash_sale"
    title = "Venta relámpago"
    summary = "N compradores pagan el mismo producto a la vez: muestra los bloqueos del sistema actual."
    params = (
        Param("buyers", "Compradores simultáneos", 100, 2, 600),
        Param("product_number", "Producto (número)", 1, 1, 2000, "1 = P00001, la oferta estrella"),
        Param("reset", "Reiniciar datos antes", True, kind="bool"),
    )

    def extra_validation(self, params, settings):
        params["buyers"] = min(params["buyers"], settings.max_virtual_users)
        return params

    async def run(self, ctx) -> None:
        p = ctx.params
        product = f"P{p['product_number']:05d}"
        users = [f"U{i:05d}" for i in range(1, p["buyers"] + 1)]

        for system in ctx.run.systems:
            if ctx.cancel.is_set() or not await prepare_system(ctx, system):
                continue
            async with make_client(ctx.settings.target_url(system), len(users) + 10, 60) as client:
                await ctx.event("phase", f"{len(users)} compradores agregan {product} al carrito…", system)
                await asyncio.gather(*(
                    client.post(f"/api/v1/carts/{u}/items", json={"product_id": product, "quantity": 1})
                    for u in users
                ), return_exceptions=True)

                await ctx.event("phase", f"¡Ya! Todos pagan {product} al mismo tiempo", system)
                metrics = MetricsCollector()
                stop = asyncio.Event()

                async def on_tick(data, system=system):
                    await ctx.tick(system, data)

                ticker = asyncio.create_task(publish_ticks(metrics, on_tick, stop))

                async def buy(user: str) -> int | None:
                    started = time.perf_counter()
                    try:
                        status = (await client.post("/api/v1/orders/checkout", json={"user_id": user})).status_code
                    except Exception:  # noqa: BLE001 - timeout o conexión = falla técnica
                        status = None
                    metrics.record("checkout", (time.perf_counter() - started) * 1000, status)
                    return status

                statuses = await asyncio.gather(*(buy(u) for u in users))
                wall = metrics.elapsed()
                stop.set()
                await ticker

            ok = sum(1 for s in statuses if s == 201)
            result = ctx.result(system)
            result.summary = metrics.summary()
            result.extra = {
                "product": product,
                "buyers": len(users),
                "orders_ok": ok,
                "payment_declined": sum(1 for s in statuses if s == 402),
                "sold_out": sum(1 for s in statuses if s == 409),
                "errors": sum(1 for s in statuses if s is None or s >= 500),
                "wall_time_s": round(wall, 2),
                "checkouts_per_s": round(ok / wall, 1) if wall else 0,
            }
            await finish_system(ctx, system)
