"""Consultas de pedidos (solo lectura)."""
from app.core.exceptions import NotFoundError
from app.repositories.order_repository import OrderRepository
from app.repositories.user_repository import UserRepository
from app.schemas.order import OrderOut
from app.services.mappers import order_doc_to_out


class OrderService:
    def __init__(self, orders: OrderRepository, users: UserRepository):
        self._orders = orders
        self._users = users

    async def get_order(self, order_id: str) -> OrderOut:
        doc = await self._orders.get(order_id)
        if doc is None:
            raise NotFoundError(f"Pedido {order_id} no existe")
        return order_doc_to_out(doc)

    async def list_user_orders(self, user_id: str) -> list[OrderOut]:
        user = await self._users.get(user_id)
        if user is None:
            raise NotFoundError(f"Usuario {user_id} no existe")
        docs = await self._orders.list_by_user(user_id, user["country"])
        return [order_doc_to_out(d) for d in docs]
