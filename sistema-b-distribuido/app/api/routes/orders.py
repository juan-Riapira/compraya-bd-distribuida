"""Rutas HTTP de pedidos y checkout."""
from fastapi import APIRouter, Depends, Header

from app.api.deps import get_checkout_service, get_order_service
from app.schemas.order import CheckoutIn, OrderOut
from app.services.checkout_service import CheckoutService
from app.services.order_service import OrderService

router = APIRouter(tags=["pedidos"])


@router.post("/orders/checkout", response_model=OrderOut, status_code=201)
async def checkout(
    body: CheckoutIn,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    service: CheckoutService = Depends(get_checkout_service),
) -> OrderOut:
    return await service.checkout(body.user_id, idempotency_key)


@router.get("/orders/{order_id}", response_model=OrderOut)
async def get_order(order_id: str, service: OrderService = Depends(get_order_service)) -> OrderOut:
    return await service.get_order(order_id)


@router.get("/users/{user_id}/orders", response_model=list[OrderOut])
async def list_user_orders(user_id: str, service: OrderService = Depends(get_order_service)) -> list[OrderOut]:
    return await service.list_user_orders(user_id)
