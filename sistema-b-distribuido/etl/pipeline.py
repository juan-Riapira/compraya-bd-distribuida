"""Orquestación del ETL: extrae por lotes, transforma, carga y valida."""
import logging
import time
from dataclasses import dataclass, field

from pymongo.asynchronous.database import AsyncDatabase
from redis.asyncio import Redis

from etl import transform as T
from etl.extract import PostgresExtractor
from etl.load import MongoLoader, RedisLoader
from etl.settings import EtlSettings
from etl.validate import Check, compare, target_checksums

log = logging.getLogger("etl")


@dataclass
class EtlReport:
    loaded: dict[str, int] = field(default_factory=dict)
    checks: list[Check] = field(default_factory=list)
    seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)


async def run(settings: EtlSettings, db: AsyncDatabase, redis: Redis, cart_ttl_s: int) -> EtlReport:
    started = time.perf_counter()
    report = EtlReport()
    mongo, cache = MongoLoader(db), RedisLoader(redis, cart_ttl_s)

    async with PostgresExtractor.snapshot(settings.source_dsn, settings.batch_size) as src:
        if settings.truncate_target:
            await mongo.truncate()

        products = stock = 0
        async for rows in src.products():
            docs = [T.product_doc(r) for r in rows]
            products += await mongo.products(docs)
            stock += await cache.stock(T.stock_entries(docs))
        report.loaded["products"] = products
        report.loaded["stock_keys"] = stock

        users = 0
        async for rows in src.users():
            users += await mongo.users([T.user_doc(r) for r in rows])
        report.loaded["users"] = users

        orders = 0
        async for rows in src.orders():
            orders += await mongo.orders([T.order_doc(r) for r in rows])
        report.loaded["orders"] = orders

        # Un carrito puede quedar partido entre dos lotes: se agrupa todo antes de cargar.
        cart_rows = [r async for batch in src.cart_items() for r in batch]
        report.loaded["carts"] = await cache.carts(T.cart_hashes(cart_rows))

        source = await src.checksums()

    report.checks = compare(source, await target_checksums(db, redis))
    report.seconds = time.perf_counter() - started
    log.info("ETL terminado en %.1f s", report.seconds)
    return report
