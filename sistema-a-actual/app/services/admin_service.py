"""Casos de uso de administración: reiniciar datos, estadísticas y consistencia.

La consistencia comprueba, para cada producto:
    stock_actual + unidades_vendidas == stock_inicial   y   stock_actual >= 0
"""
from sqlalchemy.ext.asyncio import AsyncEngine

from app.repositories.admin_repository import AdminRepository
from app.schemas.admin import ConsistencyOut, StatsOut
from app.seed.dataset import build_dataset, hot_product_ids
from app.seed.loader import seed_database


class AdminService:
    def __init__(self, engine: AsyncEngine, admin: AdminRepository):
        self._engine = engine
        self._admin = admin

    async def reset(self) -> dict:
        return await seed_database(self._engine)

    async def stats(self) -> StatsOut:
        orders, revenue = await self._admin.order_totals()
        sold = await self._admin.units_sold_by_product()
        stock = await self._admin.stock_by_product()
        return StatsOut(
            system="A",
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
        negatives = [p for p, q in stock.items() if q < 0]
        violations = [p for p in initial if stock.get(p, 0) + sold.get(p, 0) != initial[p]]
        return ConsistencyOut(
            system="A",
            products_checked=len(initial),
            units_sold=sum(sold.values()),
            negative_stock=len(negatives),
            invariant_violations=len(violations),
            cache_mismatches=None,
            consistent=not negatives and not violations,
        )
