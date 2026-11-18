"""Consultas agregadas para el panel de administración y el simulador."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Inventory, Order, OrderItem


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def stock_by_product(self) -> dict[str, int]:
        result = await self._session.execute(select(Inventory.product_id, Inventory.quantity))
        return {row.product_id: row.quantity for row in result}

    async def units_sold_by_product(self) -> dict[str, int]:
        result = await self._session.execute(
            select(OrderItem.product_id, func.sum(OrderItem.quantity)).group_by(OrderItem.product_id)
        )
        return {pid: int(qty) for pid, qty in result.all()}

    async def order_totals(self) -> tuple[int, float]:
        count, revenue = (await self._session.execute(select(func.count(Order.id), func.coalesce(func.sum(Order.total), 0)))).one()
        return int(count), float(revenue)
