"""Transformación: filas relacionales -> documentos y llaves de Redis.

Funciones puras (sin E/S). Reglas que aplican:

1. Dinero: ``NUMERIC(12,2)`` -> centavos enteros (sin errores de coma flotante).
2. Desnormalización: la categoría se embebe en el producto; los ítems y el pago
   se embeben en el pedido (3 tablas -> 1 documento).
3. Copia histórica: cada ítem guarda el nombre y el precio del momento de la compra.
4. Shard key: el pedido recibe ``country`` (del usuario) para caer en el shard
   de su región.
5. Enriquecimiento: la marca se extrae de la descripción a ``attributes``.
"""
import json
import re
from collections.abc import Iterable, Mapping
from decimal import ROUND_HALF_UP, Decimal
from itertools import groupby
from typing import Any

_BRAND = re.compile(r"marca (\w+)", re.IGNORECASE)


def to_cents(value: Decimal | float | str | None) -> int:
    if value is None:
        return 0
    return int((Decimal(str(value)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def product_doc(row: Mapping[str, Any]) -> dict:
    match = _BRAND.search(row["description"] or "")
    return {
        "_id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "price_cents": to_cents(row["price"]),
        "category": {"id": row["category_id"], "name": row["category_name"]},
        "stock": int(row["stock"]),
        "attributes": {"marca": match.group(1)} if match else {},
        "updated_at": row["created_at"],
    }


def user_doc(row: Mapping[str, Any]) -> dict:
    return {
        "_id": row["id"],
        "name": row["name"],
        "email": row["email"].lower(),
        "country": row["country"].upper(),
        "created_at": row["created_at"],
    }


def order_doc(row: Mapping[str, Any]) -> dict:
    raw_items = row["items"]
    items = json.loads(raw_items) if isinstance(raw_items, str) else raw_items
    payment = None
    if row["payment_status"] is not None:
        payment = {
            "status": row["payment_status"],
            "provider_ref": row["provider_ref"],
            "amount_cents": to_cents(row["payment_amount"]),
        }
    return {
        "_id": row["id"],
        "user_id": row["user_id"],
        "country": row["country"].upper(),
        "status": row["status"],
        "items": [
            {
                "product_id": it["product_id"],
                "name": it["name"],
                "quantity": int(it["quantity"]),
                "unit_price_cents": to_cents(it["unit_price"]),
            }
            for it in items
        ],
        "total_cents": to_cents(row["total"]),
        "payment": payment,
        "created_at": row["created_at"],
    }


def stock_entries(products: Iterable[dict]) -> dict[str, int]:
    """Existencias calientes para Redis (``stock:{id}``), tomadas del documento ya transformado."""
    return {p["_id"]: p["stock"] for p in products}


def cart_hashes(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, int]]:
    """Filas (user_id, product_id, quantity) -> {user_id: {product_id: quantity}} para ``cart:{user}``."""
    return {
        user: {r["product_id"]: int(r["quantity"]) for r in group}
        for user, group in groupby(rows, key=lambda r: r["user_id"])
    }
