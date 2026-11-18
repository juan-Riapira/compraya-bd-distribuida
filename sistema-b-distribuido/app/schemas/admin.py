"""Contrato de los endpoints de administración (idéntico en A y B)."""
from pydantic import BaseModel


class StatsOut(BaseModel):
    system: str
    orders: int
    revenue: float
    units_sold: int
    hot_stock: dict[str, int]


class ConsistencyOut(BaseModel):
    system: str
    products_checked: int
    units_sold: int
    negative_stock: int
    invariant_violations: int
    cache_mismatches: int | None
    consistent: bool
