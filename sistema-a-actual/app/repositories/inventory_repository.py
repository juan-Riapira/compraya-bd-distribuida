"""Acceso a datos de existencias, con bloqueo pesimista de filas."""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Inventory


class InventoryRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def lock_for_update(self, product_ids: list[str]) -> dict[str, int]:
        """Bloquea las filas de inventario hasta el fin de la transacción.

        Se ordenan por id para evitar interbloqueos (deadlocks) entre dos
        checkouts que piden los mismos productos en distinto orden.
        """
        stmt = (
            select(Inventory.product_id, Inventory.quantity)
            .where(Inventory.product_id.in_(sorted(product_ids)))
            .order_by(Inventory.product_id)
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        return {row.product_id: row.quantity for row in result}

    async def decrement(self, product_id: str, quantity: int) -> None:
        await self._session.execute(
            update(Inventory)
            .where(Inventory.product_id == product_id)
            .values(quantity=Inventory.quantity - quantity)
        )
