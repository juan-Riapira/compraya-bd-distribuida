"""Tabla `inventory`: existencias por producto.

En el checkout estas filas se bloquean con `SELECT ... FOR UPDATE`.
Con productos "calientes" (Black Friday) muchas transacciones esperan
la misma fila: es la causa de los bloqueos que reporta CompraYa.
"""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (CheckConstraint("quantity >= 0", name="ck_inventory_non_negative"),)

    product_id: Mapped[str] = mapped_column(String(12), ForeignKey("products.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
