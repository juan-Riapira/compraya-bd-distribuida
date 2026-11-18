"""Carritos en Redis: un HASH por usuario `cart:{user_id}` -> {product_id: cantidad}.

Agregar al carrito es un HINCRBY en memoria (microsegundos) y nunca toca la
base transaccional. El TTL limpia solos los carritos abandonados.
"""
from redis.asyncio import Redis

from app.db import keys


class CartRepository:
    def __init__(self, redis: Redis, ttl_s: int):
        self._redis = redis
        self._ttl_s = ttl_s

    async def get(self, user_id: str) -> dict[str, int]:
        raw = await self._redis.hgetall(keys.cart(user_id))
        return {pid: int(qty) for pid, qty in raw.items()}

    async def add(self, user_id: str, product_id: str, quantity: int) -> None:
        key = keys.cart(user_id)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.hincrby(key, product_id, quantity)
            pipe.expire(key, self._ttl_s)
            await pipe.execute()

    async def remove(self, user_id: str, product_id: str) -> None:
        await self._redis.hdel(keys.cart(user_id), product_id)

    async def clear(self, user_id: str) -> None:
        await self._redis.delete(keys.cart(user_id))
