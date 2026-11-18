"""Carga en el Sistema B.

MongoDB: ``ReplaceOne(upsert=True)`` por ``_id`` (y ``country`` en pedidos, que es
parte de la shard key). Volver a correr el ETL no duplica nada: es idempotente,
lo que permite repetir la migración o reanudarla si se corta.

Redis: existencias con MSET y carritos como HASH con su TTL, en pipeline.
"""
from pymongo import ReplaceOne
from pymongo.asynchronous.database import AsyncDatabase
from redis.asyncio import Redis

from app.db import keys
from app.db.mongo import ORDERS, PRODUCTS, USERS


class MongoLoader:
    def __init__(self, db: AsyncDatabase):
        self._db = db

    async def truncate(self) -> None:
        # delete_many (no drop): conserva la configuración de sharding y zonas.
        for coll in (PRODUCTS, USERS, ORDERS):
            await self._db[coll].delete_many({})

    async def _upsert(self, collection: str, docs: list[dict], key_fields: tuple[str, ...]) -> int:
        if not docs:
            return 0
        ops = [ReplaceOne({k: d[k] for k in key_fields}, d, upsert=True) for d in docs]
        result = await self._db[collection].bulk_write(ops, ordered=False)
        return result.upserted_count + result.matched_count

    async def products(self, docs: list[dict]) -> int:
        return await self._upsert(PRODUCTS, docs, ("_id",))

    async def users(self, docs: list[dict]) -> int:
        return await self._upsert(USERS, docs, ("_id",))

    async def orders(self, docs: list[dict]) -> int:
        # El filtro incluye la shard key completa para que mongos vaya a un solo shard.
        return await self._upsert(ORDERS, docs, ("country", "_id"))


class RedisLoader:
    def __init__(self, redis: Redis, cart_ttl_s: int):
        self._redis = redis
        self._cart_ttl_s = cart_ttl_s

    async def stock(self, stock_by_product: dict[str, int]) -> int:
        if stock_by_product:
            await self._redis.mset({keys.stock(p): q for p, q in stock_by_product.items()})
        return len(stock_by_product)

    async def carts(self, carts: dict[str, dict[str, int]]) -> int:
        if not carts:
            return 0
        async with self._redis.pipeline(transaction=False) as pipe:
            for user_id, items in carts.items():
                key = keys.cart(user_id)
                pipe.delete(key)
                pipe.hset(key, mapping=items)
                pipe.expire(key, self._cart_ttl_s)
            await pipe.execute()
        return len(carts)
