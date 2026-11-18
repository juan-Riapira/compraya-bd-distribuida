"""Carga el dataset en MongoDB (vía mongos) y precalienta Redis.

Uso:  python -m scripts.seed
"""
import asyncio

from app.core.config import get_settings
from app.db.mongo import MongoConnection
from app.db.redis import RedisConnection
from app.seed.loader import seed_database


async def main() -> None:
    settings = get_settings()
    mongo, redis = MongoConnection(settings), RedisConnection(settings)
    result = await seed_database(mongo.db, redis.client)
    await redis.close()
    await mongo.close()
    print(f"Sistema B sembrado: {result['categories']} categorías, {result['products']} productos, {result['users']} usuarios")


if __name__ == "__main__":
    asyncio.run(main())
