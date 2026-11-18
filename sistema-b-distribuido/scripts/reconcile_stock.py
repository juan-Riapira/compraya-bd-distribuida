"""Reconcilia las existencias de Redis con MongoDB (la fuente de verdad).

Útil tras una caída de Redis o como tarea programada nocturna. Debe correrse
SIN tráfico de checkout (una reserva en curso aún no está en MongoDB). Puede
correrse en modo --check para solo reportar diferencias.

Uso:  python -m scripts.reconcile_stock [--check]
"""
import argparse
import asyncio

from app.core.config import get_settings
from app.db.mongo import PRODUCTS, MongoConnection
from app.db.redis import RedisConnection
from app.repositories.stock_repository import StockRepository


async def reconcile(check_only: bool) -> int:
    settings = get_settings()
    mongo, redis = MongoConnection(settings), RedisConnection(settings)
    stock_repo = StockRepository(redis.client)

    truth = {d["_id"]: d["stock"] async for d in mongo.db[PRODUCTS].find({}, {"stock": 1})}
    cached = await stock_repo.get_many(list(truth))
    diffs = {pid: qty for pid, qty in truth.items() if cached.get(pid) != qty}

    print(f"Productos revisados: {len(truth)} · diferencias: {len(diffs)}")
    if diffs and not check_only:
        await stock_repo.overwrite(diffs)
        print("Redis actualizado con los valores de MongoDB.")

    await redis.close()
    await mongo.close()
    return len(diffs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="solo reportar, no corregir")
    asyncio.run(reconcile(parser.parse_args().check))
