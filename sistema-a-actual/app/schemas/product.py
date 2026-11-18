"""Contrato público de productos (idéntico en el Sistema A y el B)."""
from pydantic import BaseModel


class ProductOut(BaseModel):
    id: str
    name: str
    description: str
    price: float
    category: str
    stock: int


class ProductPage(BaseModel):
    items: list[ProductOut]
    limit: int
    offset: int
