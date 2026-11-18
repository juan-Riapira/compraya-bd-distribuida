"""Casos de uso de administración: reiniciar datos, estadísticas y consistencia.

La consistencia comprueba, para cada producto:
    stock_actual + unidades_vendidas == stock_inicial   y   stock_actual >= 0
y además que el stock en Redis coincida con MongoDB (la fuente de verdad).
"""
from pymongo.asynchronous.database import AsyncDatabase
from redis.asyncio import Redis

from app.repositories.admin_repository import AdminRepository
from app.repositories.stock_repository import StockRepository
from app.schemas.admin import ConsistencyOut, StatsOut
from app.seed.dataset import build_dataset, hot_product_ids
from app.seed.loader import seed_database


class AdminService:
    def __init__(self, db: AsyncDatabase, redis: Redis, admin: AdminRepository, stock: StockRepository):
        self._db = db
        self._redis = redis
        self._admin = admin
        self._stock = stock

    async def reset(self) -> dict:
        return await seed_database(self._db, self._redis)

    async def stats(self) -> StatsOut:
        orders, revenue = await self._admin.order_totals()
        sold = await self._admin.units_sold_by_product()
        stock = await self._admin.stock_by_product()
        return StatsOut(
            system="B",
            orders=orders,
            revenue=round(revenue, 2),
            units_sold=sum(sold.values()),
            hot_stock={pid: stock.get(pid, 0) for pid in hot_product_ids()},
        )

    async def consistency(self) -> ConsistencyOut:
        _, products, _ = build_dataset()
        initial = {p.id: p.stock for p in products}
        stock = await self._admin.stock_by_product()
        sold = await self._admin.units_sold_by_product()
        cached = await self._stock.get_many(list(stock))
        negatives = [p for p, q in stock.items() if q < 0]
        violations = [p for p in initial if stock.get(p, 0) + sold.get(p, 0) != initial[p]]
        mismatches = [p for p, q in stock.items() if cached.get(p) is not None and cached[p] != q]
        return ConsistencyOut(
            system="B",
            products_checked=len(initial),
            units_sold=sum(sold.values()),
            negative_stock=len(negatives),
            invariant_violations=len(violations),
            cache_mismatches=len(mismatches),
            consistent=not negatives and not violations and not mismatches,
        )
