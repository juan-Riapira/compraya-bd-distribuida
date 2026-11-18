"""Índices secundarios de MongoDB (se crean al arrancar; la operación es idempotente)."""
from pymongo import ASCENDING, DESCENDING
from pymongo.asynchronous.database import AsyncDatabase

from app.db.mongo import ORDERS, PRODUCTS


async def ensure_indexes(db: AsyncDatabase) -> None:
    await db[PRODUCTS].create_index([("name", ASCENDING), ("_id", ASCENDING)])
    await db[PRODUCTS].create_index([("category.name", ASCENDING), ("name", ASCENDING)])
    await db[ORDERS].create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
