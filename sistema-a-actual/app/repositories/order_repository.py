"""Acceso a datos de pedidos y pagos."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, Payment


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    def add(self, order: Order) -> None:
        self._session.add(order)

    def add_payment(self, payment: Payment) -> None:
        self._session.add(payment)

    async def get(self, order_id: str) -> Order | None:
        return await self._session.get(Order, order_id)

    async def list_by_user(self, user_id: str, limit: int = 20) -> list[Order]:
        result = await self._session.execute(
            select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc()).limit(limit)
        )
        return list(result.scalars())
