"""Comportamiento de un comprador virtual (igual para A y B).

Mezcla de acciones por peso, como en un Black Friday real:
    ver catálogo 6 · ver producto 5 · agregar al carrito 2 · pagar 1
El 80 % del interés va a las 20 ofertas del día (productos "calientes").
"""
import asyncio
import random
import time
import uuid

import httpx

from app.engine.metrics import MetricsCollector

N_USERS = 5000
N_PRODUCTS = 2000
HOT_PRODUCTS = [f"P{i:05d}" for i in range(1, 21)]
CATEGORIES = ["Celulares", "Portátiles", "Tablets", "Audio", "Monitores", "Accesorios", "Gaming"]
ACTIONS = ["browse", "view", "add", "checkout"]
WEIGHTS = [6, 5, 2, 1]


def pick_product(hot_ratio: float = 0.8) -> str:
    if random.random() < hot_ratio:
        return random.choice(HOT_PRODUCTS)
    return f"P{random.randint(21, N_PRODUCTS):05d}"


async def timed(client: httpx.AsyncClient, metrics: MetricsCollector, endpoint: str, method: str, url: str, **kw) -> int | None:
    started = time.perf_counter()
    status: int | None = None
    try:
        response = await client.request(method, url, **kw)
        status = response.status_code
    except httpx.HTTPError:
        status = None
    metrics.record(endpoint, (time.perf_counter() - started) * 1000, status)
    return status


class Shopper:
    def __init__(self, client: httpx.AsyncClient, metrics: MetricsCollector, think_time_s: tuple[float, float]):
        self._client = client
        self._metrics = metrics
        self._think = think_time_s
        self.user_id = f"U{random.randint(1, N_USERS):05d}"

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            action = random.choices(ACTIONS, WEIGHTS)[0]
            await getattr(self, f"_{action}")()
            try:
                await asyncio.wait_for(stop.wait(), timeout=random.uniform(*self._think))
            except TimeoutError:
                pass

    async def _browse(self) -> None:
        params = {"limit": 20, "offset": random.choice([0, 20, 40, 60])}
        if random.random() < 0.5:
            params["category"] = random.choice(CATEGORIES)
        await timed(self._client, self._metrics, "catalog", "GET", "/api/v1/products", params=params)

    async def _view(self) -> None:
        await timed(self._client, self._metrics, "product", "GET", f"/api/v1/products/{pick_product()}")

    async def _add(self) -> None:
        body = {"product_id": pick_product(), "quantity": random.randint(1, 2)}
        await timed(self._client, self._metrics, "add_to_cart", "POST", f"/api/v1/carts/{self.user_id}/items", json=body)

    async def _checkout(self) -> None:
        await timed(
            self._client, self._metrics, "checkout", "POST", "/api/v1/orders/checkout",
            json={"user_id": self.user_id}, headers={"Idempotency-Key": uuid.uuid4().hex},
        )
