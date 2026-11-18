"""Contrato público del carrito (idéntico en el Sistema A y el B)."""
from pydantic import BaseModel, Field


class CartItemIn(BaseModel):
    product_id: str
    quantity: int = Field(gt=0, le=20)


class CartItemOut(BaseModel):
    product_id: str
    quantity: int
    unit_price: float
    subtotal: float


class CartOut(BaseModel):
    user_id: str
    items: list[CartItemOut]
    total: float
