"""Acceso a datos del carrito (tablas carts y cart_items)."""
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Cart, CartItem


class CartRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, user_id: str) -> Cart | None:
        # populate_existing: recarga los ítems aunque el carrito ya esté en la sesión.
        stmt = select(Cart).where(Cart.user_id == user_id).execution_options(populate_existing=True)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: str) -> Cart:
        await self._session.execute(
            insert(Cart).values(user_id=user_id).on_conflict_do_nothing(index_elements=[Cart.user_id])
        )
        return await self.get(user_id)  # type: ignore[return-value]

    async def upsert_item(self, cart_id: int, product_id: str, quantity: int, unit_price: Decimal) -> None:
        stmt = insert(CartItem).values(
            cart_id=cart_id, product_id=product_id, quantity=quantity, unit_price=unit_price
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[CartItem.cart_id, CartItem.product_id],
            set_={"quantity": CartItem.quantity + quantity, "unit_price": unit_price},
        )
        await self._session.execute(stmt)

    async def remove_item(self, cart_id: int, product_id: str) -> None:
        await self._session.execute(
            delete(CartItem).where(CartItem.cart_id == cart_id, CartItem.product_id == product_id)
        )

    async def clear(self, cart_id: int) -> None:
        await self._session.execute(delete(CartItem).where(CartItem.cart_id == cart_id))
