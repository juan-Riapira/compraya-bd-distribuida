"""Casos de uso del carrito (vive en Redis, no en la base transaccional)."""
from app.core.exceptions import NotFoundError
from app.repositories.cart_repository import CartRepository
from app.repositories.user_repository import UserRepository
from app.schemas.cart import CartItemIn, CartOut
from app.services.catalog_service import CatalogService
from app.services.mappers import cart_to_out


class CartService:
    def __init__(self, carts: CartRepository, users: UserRepository, catalog: CatalogService):
        self._carts = carts
        self._users = users
        self._catalog = catalog

    async def get_cart(self, user_id: str) -> CartOut:
        quantities = await self._carts.get(user_id)
        statics = await self._catalog.get_static_many(list(quantities))
        return cart_to_out(user_id, quantities, statics)

    async def add_item(self, user_id: str, item: CartItemIn) -> CartOut:
        if await self._users.get(user_id) is None:
            raise NotFoundError(f"Usuario {user_id} no existe")
        if item.product_id not in await self._catalog.get_static_many([item.product_id]):
            raise NotFoundError(f"Producto {item.product_id} no existe")
        await self._carts.add(user_id, item.product_id, item.quantity)
        return await self.get_cart(user_id)

    async def remove_item(self, user_id: str, product_id: str) -> CartOut:
        await self._carts.remove(user_id, product_id)
        return await self.get_cart(user_id)
