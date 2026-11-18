"""Casos de uso del carrito de compras."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.repositories.cart_repository import CartRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.schemas.cart import CartItemIn, CartOut
from app.services.mappers import cart_to_out


class CartService:
    def __init__(
        self,
        session: AsyncSession,
        carts: CartRepository,
        products: ProductRepository,
        users: UserRepository,
    ):
        self._session = session
        self._carts = carts
        self._products = products
        self._users = users

    async def get_cart(self, user_id: str) -> CartOut:
        return cart_to_out(user_id, await self._carts.get(user_id))

    async def add_item(self, user_id: str, item: CartItemIn) -> CartOut:
        async with self._session.begin():
            if not await self._users.exists(user_id):
                raise NotFoundError(f"Usuario {user_id} no existe")
            product = await self._products.get(item.product_id)
            if product is None:
                raise NotFoundError(f"Producto {item.product_id} no existe")
            cart = await self._carts.get_or_create(user_id)
            await self._carts.upsert_item(cart.id, product.id, item.quantity, product.price)
        return await self.get_cart(user_id)

    async def remove_item(self, user_id: str, product_id: str) -> CartOut:
        async with self._session.begin():
            cart = await self._carts.get(user_id)
            if cart is not None:
                await self._carts.remove_item(cart.id, product_id)
        return await self.get_cart(user_id)
