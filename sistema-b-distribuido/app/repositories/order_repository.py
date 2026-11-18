"""Acceso a la colección `orders`.

Un pedido es UN documento con sus ítems y su pago embebidos: se escribe y se
lee en una sola operación, sin JOIN entre orders / order_items / payments.

Shard key: {country: 1, _id: 1} + zonas por región. Los pedidos de CO/MX/PE
viven en el shard "norte" y los de CL/AR en el shard "sur", cerca de sus
usuarios (reducción de latencia por región).
"""
from pymongo import DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

from app.db.mongo import ORDERS


class OrderRepository:
    def __init__(self, db: AsyncDatabase):
        self._col = db[ORDERS]

    async def insert(self, order: dict) -> None:
        # Un solo documento = escritura atómica en un solo shard, sin transacción.
        await self._col.insert_one(order)

    async def get(self, order_id: str, country: str | None = None) -> dict | None:
        # Con `country` la consulta va a un shard; sin él, mongos pregunta a todos.
        query = {"_id": order_id, **({"country": country} if country else {})}
        return await self._col.find_one(query)

    async def list_by_user(self, user_id: str, country: str, limit: int = 20) -> list[dict]:
        cursor = (
            self._col.find({"country": country, "user_id": user_id})
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)
