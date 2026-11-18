"""Validación posterior a la carga: mismas cuentas y mismas sumas en origen y destino.

Si algo no cuadra, el reporte lo marca y el script termina con código 1, así
la migración no se da por buena en silencio.
"""
from dataclasses import dataclass

from pymongo.asynchronous.database import AsyncDatabase
from redis.asyncio import Redis

from app.db.mongo import ORDERS, PRODUCTS, USERS


@dataclass(frozen=True)
class Check:
    name: str
    source: int
    target: int

    @property
    def ok(self) -> bool:
        return self.source == self.target


async def _sum(db: AsyncDatabase, coll: str, field: str) -> int:
    rows = await (await db[coll].aggregate([{"$group": {"_id": None, "s": {"$sum": f"${field}"}}}])).to_list(1)
    return int(rows[0]["s"]) if rows else 0


async def target_checksums(db: AsyncDatabase, redis: Redis) -> dict[str, int]:
    carts = 0
    async for _ in redis.scan_iter(match="cart:*", count=1000):
        carts += 1
    return {
        "products": await db[PRODUCTS].count_documents({}),
        "users": await db[USERS].count_documents({}),
        "orders": await db[ORDERS].count_documents({}),
        "stock_units": await _sum(db, PRODUCTS, "stock"),
        "revenue_cents": await _sum(db, ORDERS, "total_cents"),
        "carts": carts,
    }


def compare(source: dict[str, int], target: dict[str, int]) -> list[Check]:
    return [Check(name, source[name], target.get(name, -1)) for name in source]
