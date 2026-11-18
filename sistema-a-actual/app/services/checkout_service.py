"""Caso de uso de checkout del Sistema A (diseño heredado).

Flujo dentro de UNA transacción de PostgreSQL:

    1. leer el carrito
    2. SELECT ... FOR UPDATE sobre el inventario      <- se toman bloqueos
    3. validar existencias y crear el pedido
    4. cobrar en la pasarela externa (≈80 ms)          <- bloqueos retenidos
    5. descontar inventario, registrar pago, vaciar carrito
    6. COMMIT                                          <- se liberan bloqueos

Mientras dura el paso 4 nadie más puede comprar esos productos. En Black
Friday, con pocos productos "calientes", las transacciones se encolan,
el pool de conexiones se agota y aparecen los timeouts y "fallas de pago"
que describe el enunciado. El Sistema B saca el cobro fuera de los bloqueos.
"""
import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmptyCartError, InsufficientStockError, PaymentDeclinedError
from app.integrations.payment_gateway import PaymentGateway
from app.models import Order, OrderItem, Payment
from app.repositories.cart_repository import CartRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.order import OrderOut
from app.services.mappers import order_to_out


class CheckoutService:
    def __init__(
        self,
        session: AsyncSession,
        carts: CartRepository,
        inventory: InventoryRepository,
        orders: OrderRepository,
        gateway: PaymentGateway,
    ):
        self._session = session
        self._carts = carts
        self._inventory = inventory
        self._orders = orders
        self._gateway = gateway

    async def checkout(self, user_id: str) -> OrderOut:
        async with self._session.begin():
            cart = await self._carts.get(user_id)
            if cart is None or not cart.items:
                raise EmptyCartError("El carrito está vacío")

            wanted = {i.product_id: i.quantity for i in cart.items}
            stock = await self._inventory.lock_for_update(list(wanted))
            for product_id, qty in wanted.items():
                if stock.get(product_id, 0) < qty:
                    raise InsufficientStockError(f"Sin existencias suficientes de {product_id}")

            order_id = str(uuid.uuid4())
            total = sum((i.unit_price * i.quantity for i in cart.items), Decimal("0"))
            order = Order(
                id=order_id,
                user_id=user_id,
                status="PAID",
                total=total,
                items=[
                    OrderItem(product_id=i.product_id, quantity=i.quantity, unit_price=i.unit_price)
                    for i in cart.items
                ],
            )

            # Llamada externa CON los bloqueos de inventario tomados.
            result = await self._gateway.charge(order_id, total)
            if not result.approved:
                # El rollback descarta el pedido: no queda rastro del intento.
                raise PaymentDeclinedError("La pasarela rechazó el pago")

            for product_id, qty in wanted.items():
                await self._inventory.decrement(product_id, qty)
            self._orders.add(order)
            await self._session.flush()
            self._orders.add_payment(
                Payment(order_id=order_id, amount=total, status="APPROVED", provider_ref=result.provider_ref)
            )
            await self._carts.clear(cart.id)

        saved = await self._orders.get(order_id)
        await self._session.refresh(saved, attribute_names=["payment", "items"])
        return order_to_out(saved)  # type: ignore[arg-type]
