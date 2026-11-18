"""Acceso a la colección `products` (fuente de verdad del catálogo y del stock).

Documento de ejemplo (todo lo que se muestra de un producto, en UNA lectura):
    {
      "_id": "P00001", "name": "Portátil Nova 859", "description": "...",
      "price_cents": 69845,
      "category": {"id": 2, "name": "Portátiles"},     <- desnormalizado, sin JOIN
      "stock": 300,
      "attributes": {"marca": "Nova", "garantia_meses": 12},  <- esquema flexible
      "updated_at": ISODate(...)
    }
Shard key: {_id: "hashed"} -> los productos se reparten uniformemente entre shards.
"""
from datetime import UTC, datetime

from pymongo import ASCENDING
from pymongo.asynchronous.database import AsyncDatabase

from app.db.mongo import PRODUCTS


class ProductRepository:
    def __init__(self, db: AsyncDatabase):
        self._col = db[PRODUCTS]

    async def list_page(self, limit: int, offset: int, category: str | None = None) -> list[dict]:
        query = {"category.name": category} if category else {}
        cursor = self._col.find(query).sort([("name", ASCENDING), ("_id", ASCENDING)]).skip(offset).limit(limit)
        return await cursor.to_list(length=limit)

    async def get(self, product_id: str) -> dict | None:
        return await self._col.find_one({"_id": product_id})

    async def get_many(self, product_ids: list[str]) -> dict[str, dict]:
        docs = await self._col.find({"_id": {"$in": product_ids}}).to_list(length=len(product_ids))
        return {d["_id"]: d for d in docs}

    async def decrement_stock(self, product_id: str, quantity: int) -> bool:
        """Descuenta stock solo si alcanza (condición atómica en el documento)."""
        result = await self._col.update_one(
            {"_id": product_id, "stock": {"$gte": quantity}},
            {"$inc": {"stock": -quantity}, "$set": {"updated_at": datetime.now(UTC)}},
        )
        return result.modified_count == 1

    async def increment_stock(self, product_id: str, quantity: int) -> None:
        """Acción compensatoria: devuelve unidades descontadas."""
        await self._col.update_one(
            {"_id": product_id},
            {"$inc": {"stock": quantity}, "$set": {"updated_at": datetime.now(UTC)}},
        )

    async def list_categories(self) -> list[str]:
        return sorted(await self._col.distinct("category.name"))
