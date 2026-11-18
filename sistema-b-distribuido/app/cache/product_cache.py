"""Caché *cache-aside* del catálogo en Redis.

Guarda la parte "estática" del producto (nombre, precio, categoría) como JSON.
El stock NO se cachea aquí: se superpone desde `stock:{id}`, así una venta
nunca deja una página del catálogo con existencias viejas.
"""
import json

from redis.asyncio import Redis

from app.db import keys


class ProductCache:
    def __init__(self, redis: Redis, product_ttl_s: int, list_ttl_s: int):
        self._redis = redis
        self._product_ttl_s = product_ttl_s
        self._list_ttl_s = list_ttl_s

    async def get_many(self, product_ids: list[str]) -> dict[str, dict]:
        if not product_ids:
            return {}
        raw = await self._redis.mget([keys.product(p) for p in product_ids])
        return {pid: json.loads(v) for pid, v in zip(product_ids, raw) if v is not None}

    async def set_many(self, products: list[dict]) -> None:
        async with self._redis.pipeline(transaction=False) as pipe:
            for p in products:
                pipe.set(keys.product(p["id"]), json.dumps(p), ex=self._product_ttl_s)
            await pipe.execute()

    async def get_list(self, category: str | None, limit: int, offset: int) -> list[dict] | None:
        raw = await self._redis.get(keys.product_list(category, limit, offset))
        return json.loads(raw) if raw is not None else None

    async def set_list(self, category: str | None, limit: int, offset: int, products: list[dict]) -> None:
        await self._redis.set(keys.product_list(category, limit, offset), json.dumps(products), ex=self._list_ttl_s)
