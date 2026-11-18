"""Contrato público de pedidos (idéntico en el Sistema A y el B)."""
from datetime import datetime

from pydantic import BaseModel


class CheckoutIn(BaseModel):
    user_id: str


class OrderItemOut(BaseModel):
    product_id: str
    quantity: int
    unit_price: float


class PaymentOut(BaseModel):
    status: str
    provider_ref: str
    amount: float


class OrderOut(BaseModel):
    id: str
    user_id: str
    status: str
    total: float
    created_at: datetime
    items: list[OrderItemOut]
    payment: PaymentOut | None = None
