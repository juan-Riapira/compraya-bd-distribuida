"""Verifica que, tras la prueba de carga, NO se haya vendido más de lo que había.

Invariante para cada producto:   stock_actual + unidades_vendidas == stock_inicial
y además stock_actual >= 0. En el Sistema B también compara Redis con MongoDB.

Uso:
    python consistency_check.py --system A --pg-dsn postgresql://compraya:compraya@localhost:5432/compraya
    python consistency_check.py --system B --mongo-uri mongodb://localhost:27017 --redis-url redis://localhost:6379/0
"""
import argparse
import asyncio
import importlib.util
import json
import time
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = HERE / "resultados"


def initial_stock() -> dict[str, int]:
    path = HERE.parent / "sistema-a-actual" / "app" / "seed" / "dataset.py"
    spec = importlib.util.spec_from_file_location("dataset", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    _, products, _ = module.build_dataset()
    return {p.id: p.stock for p in products}


async def state_a(dsn: str) -> tuple[dict[str, int], dict[str, int], int]:
    import asyncpg

    conn = await asyncpg.connect(dsn)
    stock = {r["product_id"]: r["quantity"] for r in await conn.fetch("SELECT product_id, quantity FROM inventory")}
    sold = {
        r["product_id"]: r["sold"]
        for r in await conn.fetch("SELECT product_id, SUM(quantity)::int AS sold FROM order_items GROUP BY product_id")
    }
    orders = await conn.fetchval("SELECT COUNT(*) FROM orders")
    await conn.close()
    return stock, sold, orders


def state_b(mongo_uri: str, redis_url: str) -> tuple[dict[str, int], dict[str, int], int, int]:
    import redis
    from pymongo import MongoClient

    db = MongoClient(mongo_uri).compraya
    stock = {d["_id"]: d["stock"] for d in db.products.find({}, {"stock": 1})}
    sold: dict[str, int] = {}
    for row in db.orders.aggregate([{"$unwind": "$items"}, {"$group": {"_id": "$items.product_id", "sold": {"$sum": "$items.quantity"}}}]):
        sold[row["_id"]] = row["sold"]
    orders = db.orders.count_documents({})
    r = redis.Redis.from_url(redis_url, decode_responses=True)
    ids = list(stock)
    cached = dict(zip(ids, r.mget([f"stock:{p}" for p in ids])))
    redis_diffs = sum(1 for p in ids if cached[p] is not None and int(cached[p]) != stock[p])
    return stock, sold, orders, redis_diffs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=["A", "B"], required=True)
    parser.add_argument("--pg-dsn", default="postgresql://compraya:compraya@localhost:5432/compraya")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--redis-url", default="redis://localhost:6379/0")
    parser.add_argument("--tag", default="", help="sufijo para el archivo de salida")
    parser.add_argument("--settle-s", type=float, default=10, help="espera a que terminen los checkouts en curso")
    args = parser.parse_args()

    time.sleep(args.settle_s)
    initial = initial_stock()
    redis_diffs = None
    if args.system == "A":
        stock, sold, orders = asyncio.run(state_a(args.pg_dsn))
    else:
        stock, sold, orders, redis_diffs = state_b(args.mongo_uri, args.redis_url)

    negatives = [p for p, q in stock.items() if q < 0]
    broken = [p for p in initial if stock.get(p, 0) + sold.get(p, 0) != initial[p]]
    sold_out_hot = [p for p in (f"P{i:05d}" for i in range(1, 21)) if stock.get(p) == 0]
    report = {
        "system": args.system,
        "orders": orders,
        "units_sold": sum(sold.values()),
        "negative_stock_products": len(negatives),
        "invariant_violations": len(broken),
        "hot_products_sold_out": len(sold_out_hot),
        "redis_vs_mongo_diffs": redis_diffs,
        "consistent": not negatives and not broken and not redis_diffs,
    }
    print(json.dumps(report, indent=2))
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"consistencia_{args.system}{args.tag}.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
