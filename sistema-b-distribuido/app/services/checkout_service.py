"""Caso de uso de checkout del Sistema B (diseño propuesto, patrón *saga*).

    1. idempotencia: un reintento no cobra dos veces                  (Redis)
    2. leer carrito y precios                                          (Redis)
    3. RESERVAR stock de todo el carrito en un script Lua atómico      (Redis)
    4. cobrar en la pasarela externa — SIN bloqueos en la base         (externo)
    5. confirmar el descuento de stock, producto por producto, EN
       PARALELO en el shard de cada uno (actualización atómica)        (MongoDB)
    6. guardar el pedido como UN documento en el shard de su región    (MongoDB)
    7. vaciar carrito                                                  (Redis)

Si algo falla después del paso 3, cada paso hecho se deshace con su acción
compensatoria (devolver reserva, revertir descuentos, reembolsar).

¿Por qué no una transacción multi-documento? Los productos están repartidos
en varios shards, así que una transacción sería *distribuida* (two-phase
commit entre shards): costosa y con bloqueos de documentos. Aquí no hace
falta: la reserva atómica en Redis ya impide vender de más, y cada
actualización en MongoDB es atómica por documento.

La diferencia clave con el Sistema A: durante los ≈80 ms del cobro no hay
ninguna fila ni documento bloqueado, así que las compras del mismo producto
"caliente" avanzan en paralelo.
"""
import asyncio
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.core.exceptions import (
    DuplicateRequestError,
    EmptyCartError,
    InsufficientStockError,
    NotFoundError,
    PaymentDeclinedError,
)
from app.integrations.payment_gateway import PaymentGateway
from app.repositories.cart_repository import CartRepository
from app.repositories.idempotency_repository import IdempotencyRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.stock_repository import MissingStockKeyError, StockRepository, StockReservationError
from app.repositories.user_repository import UserRepository
from app.schemas.order import OrderOut
from app.services.catalog_service import CatalogService
from app.services.mappers import order_doc_to_out

log = logging.getLogger(__name__)


class _StockConflict(Exception):
    """MongoDB no confirmó un descuento (Redis y MongoDB se desincronizaron)."""

    def __init__(self, product_id: str):
        self.product_id = product_id


class CheckoutService:
    def __init__(
        self,
        users: UserRepository,
        products: ProductRepository,
        orders: OrderRepository,
        carts: CartRepository,
        stock: StockRepository,
        idempotency: IdempotencyRepository,
        catalog: CatalogService,
        gateway: PaymentGateway,
    ):
        self._users = users
        self._products = products
        self._orders = orders
        self._carts = carts
        self._stock = stock
        self._idem = idempotency
        self._catalog = catalog
        self._gateway = gateway

    # ------------------------------------------------------------------ API
    async def checkout(self, user_id: str, idempotency_key: str | None = None) -> OrderOut:
        if idempotency_key:
            previous = await self._idem.acquire(idempotency_key)
            if self._idem.is_pending(previous):
                raise DuplicateRequestError("Ya hay un checkout en curso con esa Idempotency-Key")
            if previous is not None:
                return await self._existing_order(previous)
        try:
            order = await self._checkout(user_id)
        except BaseException:
            if idempotency_key:
                await self._idem.release(idempotency_key)
            raise
        if idempotency_key:
            await self._idem.complete(idempotency_key, order["_id"])
        return order_doc_to_out(order)

    # ------------------------------------------------------------ la saga
    async def _checkout(self, user_id: str) -> dict:
        user = await self._users.get(user_id)
        if user is None:
            raise NotFoundError(f"Usuario {user_id} no existe")
        quantities = await self._carts.get(user_id)
        if not quantities:
            raise EmptyCartError("El carrito está vacío")
        statics = await self._catalog.get_static_many(list(quantities))

        await self._reserve(quantities)                                   # paso 3
        order = self._build_order(user_id, user["country"], quantities, statics)
        payment_ref: str | None = None
        committed: list[str] = []
        try:
            result = await self._gateway.charge(order["_id"], Decimal(order["total_cents"]) / 100)  # paso 4
            if not result.approved:
                raise PaymentDeclinedError("La pasarela rechazó el pago")
            payment_ref = result.provider_ref
            order["payment"] = {
                "status": "APPROVED",
                "provider_ref": payment_ref,
                "amount_cents": order["total_cents"],
                "at": datetime.now(UTC),
            }
            await self._commit_stock(quantities, committed)               # paso 5
            await self._orders.insert(order)                              # paso 6
        except _StockConflict as exc:
            await self._compensate(quantities, committed, payment_ref)
            await self._resync_stock(exc.product_id)
            raise InsufficientStockError(f"Sin existencias suficientes de {exc.product_id}") from None
        except BaseException:
            await self._compensate(quantities, committed, payment_ref)
            raise

        await self._carts.clear(user_id)                                  # paso 7
        return order

    async def _reserve(self, quantities: dict[str, int]) -> None:
        for attempt in range(2):
            try:
                await self._stock.reserve(quantities)
                return
            except MissingStockKeyError:
                if attempt == 1:
                    raise
                docs = await self._products.get_many(list(quantities))
                await self._stock.warm({pid: d["stock"] for pid, d in docs.items()})
            except StockReservationError as exc:
                raise InsufficientStockError(f"Sin existencias suficientes de {exc.product_id}") from None

    async def _commit_stock(self, quantities: dict[str, int], committed: list[str]) -> None:
        """Descuenta en MongoDB en paralelo; cada shard atiende sus productos."""
        pids = sorted(quantities)
        results = await asyncio.gather(
            *(self._products.decrement_stock(pid, quantities[pid]) for pid in pids), return_exceptions=True
        )
        committed.extend(pid for pid, ok in zip(pids, results) if ok is True)
        for pid, ok in zip(pids, results):
            if isinstance(ok, BaseException):
                raise ok
            if not ok:
                raise _StockConflict(pid)

    async def _compensate(self, quantities: dict[str, int], committed: list[str], payment_ref: str | None) -> None:
        """Deshace en orden inverso lo que ya se hizo. Nunca queda dinero cobrado
        sin pedido ni stock descontado sin venta."""
        if committed:
            await asyncio.gather(*(self._products.increment_stock(pid, quantities[pid]) for pid in committed))
        await self._stock.release(quantities)
        if payment_ref is not None:
            await self._gateway.refund(payment_ref)

    async def _resync_stock(self, product_id: str) -> None:
        doc = await self._products.get(product_id)
        if doc is not None:
            log.warning("Reconciliando stock de %s en Redis con MongoDB (%s)", product_id, doc["stock"])
            await self._stock.overwrite({product_id: doc["stock"]})

    async def _existing_order(self, order_id: str) -> OrderOut:
        doc = await self._orders.get(order_id)
        if doc is None:
            raise NotFoundError(f"Pedido {order_id} no existe")
        return order_doc_to_out(doc)

    @staticmethod
    def _build_order(user_id: str, country: str, quantities: dict[str, int], statics: dict[str, dict]) -> dict:
        items = [
            {
                "product_id": pid,
                "name": statics[pid]["name"],
                "quantity": qty,
                "unit_price_cents": statics[pid]["price_cents"],
            }
            for pid, qty in sorted(quantities.items())
        ]
        return {
            "_id": str(uuid.uuid4()),
            "user_id": user_id,
            "country": country,  # parte de la shard key -> shard de su región
            "status": "PAID",
            "items": items,
            "total_cents": sum(i["unit_price_cents"] * i["quantity"] for i in items),
            "payment": None,
            "created_at": datetime.now(UTC),
        }
