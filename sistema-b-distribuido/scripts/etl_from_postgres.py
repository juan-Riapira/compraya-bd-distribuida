"""Migra los datos del Sistema A (PostgreSQL) al Sistema B (MongoDB + Redis).

Uso:
    python -m scripts.etl_from_postgres                 # carga incremental (upsert)
    ETL_TRUNCATE_TARGET=true python -m scripts.etl_from_postgres   # migración en limpio

Variables: ETL_SOURCE_DSN, ETL_BATCH_SIZE, ETL_TRUNCATE_TARGET (+ MONGO_URI y REDIS_URL del Sistema B).
"""
import asyncio
import sys

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.indexes import ensure_indexes
from app.db.mongo import MongoConnection
from app.db.redis import RedisConnection
from etl.pipeline import run
from etl.settings import get_etl_settings


async def main() -> int:
    settings, etl_settings = get_settings(), get_etl_settings()
    configure_logging(settings.log_level)
    mongo, redis = MongoConnection(settings), RedisConnection(settings)
    try:
        report = await run(etl_settings, mongo.db, redis.client, settings.cart_ttl_s)
        await ensure_indexes(mongo.db)
    finally:
        await redis.close()
        await mongo.close()

    print(f"\nCargado: {report.loaded}  ({report.seconds:.1f} s)\n")
    print(f"{'Control':<15}{'PostgreSQL':>14}{'MongoDB/Redis':>16}  Estado")
    for c in report.checks:
        print(f"{c.name:<15}{c.source:>14,}{c.target:>16,}  {'OK' if c.ok else 'DIFERENTE'}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
