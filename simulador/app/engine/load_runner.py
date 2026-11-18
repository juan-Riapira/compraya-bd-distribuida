"""Motor de carga: lanza N compradores virtuales y publica métricas cada segundo."""
import asyncio
from collections.abc import Awaitable, Callable

import httpx

from app.engine.metrics import MetricsCollector
from app.engine.shopper import Shopper

TickCallback = Callable[[dict], Awaitable[None]]


def make_client(base_url: str, connections: int, timeout_s: float) -> httpx.AsyncClient:
    limits = httpx.Limits(max_connections=connections, max_keepalive_connections=connections)
    return httpx.AsyncClient(base_url=base_url, limits=limits, timeout=timeout_s)


async def publish_ticks(metrics: MetricsCollector, on_tick: TickCallback, stop: asyncio.Event) -> None:
    """Cada segundo cerrado se envía a la interfaz."""
    sent = 0
    while not stop.is_set():
        await asyncio.sleep(0.25)
        closed = int(metrics.elapsed())
        while sent < closed:
            await on_tick(metrics.second(sent))
            sent += 1
    await on_tick(metrics.second(sent))


async def run_load(
    base_url: str,
    users: int,
    duration_s: int,
    ramp_up_s: int,
    think_time_s: tuple[float, float],
    timeout_s: float,
    on_tick: TickCallback,
    cancel: asyncio.Event,
    during: Callable[[MetricsCollector], Awaitable[None]] | None = None,
) -> MetricsCollector:
    """Corre la carga y devuelve las métricas. `during` permite inyectar acciones
    (por ejemplo, apagar un nodo) mientras la carga sigue."""
    metrics = MetricsCollector()
    stop = asyncio.Event()
    async with make_client(base_url, users + 10, timeout_s) as client:
        ticker = asyncio.create_task(publish_ticks(metrics, on_tick, stop))
        tasks: list[asyncio.Task] = []

        async def spawn() -> None:
            for i in range(users):
                if stop.is_set():
                    return
                tasks.append(asyncio.create_task(Shopper(client, metrics, think_time_s).run(stop)))
                if ramp_up_s:
                    await asyncio.sleep(ramp_up_s / users)

        spawner = asyncio.create_task(spawn())
        extra = asyncio.create_task(during(metrics)) if during else None
        try:
            await asyncio.wait_for(cancel.wait(), timeout=duration_s)
        except TimeoutError:
            pass
        stop.set()
        spawner.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if extra:
            extra.cancel()
            await asyncio.gather(extra, return_exceptions=True)
        await ticker
    return metrics
