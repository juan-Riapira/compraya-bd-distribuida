"""Carga del dataset en MongoDB (vía mongos) y precalentamiento de Redis.

La usan el script `python -m scripts.seed` y el endpoint `POST /admin/reset`
que llama el simulador antes de cada prueba. Usa EXACTAMENTE el mismo
dataset que el Sistema A.
"""
from datetime import UTC, datetime

from pymongo.asynchronous.database import AsyncDatabase
from redis.asyncio import Redis

from app.db.indexes import ensure_indexes
from app.db.mongo import ORDERS, PRODUCTS, USERS
from app.repositories.stock_repository import StockRepository
from app.seed.dataset import build_dataset

BATCH = 1000


async def seed_database(db: AsyncDatabase, redis: Redis) -> dict:
    categories, products, users = build_dataset()
    now = datetime.now(UTC)

    # delete_many (no drop) para conservar la configuración de sharding.
    for coll in (USERS, PRODUCTS, ORDERS):
        await db[coll].delete_many({})

    product_docs = [
        {
            "_id": p.id,
            "name": p.name,
            "description": p.description,
            "price_cents": round(p.price * 100),
            "category": {"id": p.category_id, "name": p.category},
            "stock": p.stock,
            "attributes": p.attributes,
            "updated_at": now,
        }
        for p in products
    ]
    user_docs = [{"_id": u.id, "name": u.name, "email": u.email, "country": u.country, "created_at": now} for u in users]

    for coll, docs in ((PRODUCTS, product_docs), (USERS, user_docs)):
        for i in range(0, len(docs), BATCH):
            await db[coll].insert_many(docs[i : i + BATCH], ordered=False)
    await ensure_indexes(db)

    await redis.flushdb()
    await StockRepository(redis).overwrite({p.id: p.stock for p in products})
    return {"categories": len(categories), "products": len(products), "users": len(users)}
