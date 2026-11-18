"""Consultas de pedidos (solo lectura)."""
from app.core.exceptions import NotFoundError
from app.repositories.order_repository import OrderRepository
from app.schemas.order import OrderOut
from app.services.mappers import order_to_out


class OrderService:
    def __init__(self, orders: OrderRepository):
        self._orders = orders

    async def get_order(self, order_id: str) -> OrderOut:
        order = await self._orders.get(order_id)
        if order is None:
            raise NotFoundError(f"Pedido {order_id} no existe")
        return order_to_out(order)

    async def list_user_orders(self, user_id: str) -> list[OrderOut]:
        return [order_to_out(o) for o in await self._orders.list_by_user(user_id)]
