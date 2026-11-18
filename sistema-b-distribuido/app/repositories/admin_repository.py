"""Consultas agregadas para el panel de administración y el simulador."""
from pymongo.asynchronous.database import AsyncDatabase

from app.db.mongo import ORDERS, PRODUCTS


class AdminRepository:
    def __init__(self, db: AsyncDatabase):
        self._db = db

    async def stock_by_product(self) -> dict[str, int]:
        return {d["_id"]: d["stock"] async for d in self._db[PRODUCTS].find({}, {"stock": 1})}

    async def units_sold_by_product(self) -> dict[str, int]:
        pipeline = [
            {"$unwind": "$items"},
            {"$group": {"_id": "$items.product_id", "sold": {"$sum": "$items.quantity"}}},
        ]
        cursor = await self._db[ORDERS].aggregate(pipeline)
        return {row["_id"]: row["sold"] async for row in cursor}

    async def order_totals(self) -> tuple[int, float]:
        cursor = await self._db[ORDERS].aggregate(
            [{"$group": {"_id": None, "n": {"$sum": 1}, "cents": {"$sum": "$total_cents"}}}]
        )
        rows = await cursor.to_list(length=1)
        return (rows[0]["n"], rows[0]["cents"] / 100) if rows else (0, 0.0)
