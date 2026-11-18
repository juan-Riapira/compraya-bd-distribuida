"""Llaves de idempotencia en Redis para el checkout.

Si el cliente reintenta el mismo checkout (doble clic, red inestable en
Black Friday) con el mismo encabezado `Idempotency-Key`, se devuelve el
pedido ya creado en lugar de cobrar dos veces.
"""
from redis.asyncio import Redis

from app.db import keys

_PENDING = "__pending__"


class IdempotencyRepository:
    def __init__(self, redis: Redis, ttl_s: int):
        self._redis = redis
        self._ttl_s = ttl_s

    async def acquire(self, key: str) -> str | None:
        """Reclama la llave. Devuelve None si es nueva, o el valor previo si ya existía."""
        if await self._redis.set(keys.idempotency(key), _PENDING, nx=True, ex=self._ttl_s):
            return None
        return await self._redis.get(keys.idempotency(key))

    async def complete(self, key: str, order_id: str) -> None:
        await self._redis.set(keys.idempotency(key), order_id, ex=self._ttl_s)

    async def release(self, key: str) -> None:
        await self._redis.delete(keys.idempotency(key))

    @staticmethod
    def is_pending(value: str | None) -> bool:
        return value == _PENDING
