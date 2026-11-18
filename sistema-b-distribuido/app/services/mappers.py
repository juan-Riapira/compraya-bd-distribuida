"""Traducción entre documentos de MongoDB y los DTO públicos (schemas).

El dinero se guarda en centavos enteros (`price_cents`) para no acumular
errores de punto flotante; hacia afuera se expone en unidades, igual que A.
"""
from app.schemas.cart import CartItemOut, CartOut
from app.schemas.order import OrderItemOut, OrderOut, PaymentOut
from app.schemas.product import ProductOut


def cents_to_amount(cents: int) -> float:
    return round(cents / 100, 2)


def product_doc_to_static(doc: dict) -> dict:
    """Parte cacheable de un producto (sin stock)."""
    return {
        "id": doc["_id"],
        "name": doc["name"],
        "description": doc["description"],
        "price_cents": doc["price_cents"],
        "category": doc["category"]["name"],
    }


def static_to_out(static: dict, stock: int) -> ProductOut:
    return ProductOut(
        id=static["id"],
        name=static["name"],
        description=static["description"],
        price=cents_to_amount(static["price_cents"]),
        category=static["category"],
        stock=stock,
    )


def cart_to_out(user_id: str, quantities: dict[str, int], statics: dict[str, dict]) -> CartOut:
    items = []
    for pid, qty in sorted(quantities.items()):
        if pid not in statics:
            continue
        unit = cents_to_amount(statics[pid]["price_cents"])
        items.append(CartItemOut(product_id=pid, quantity=qty, unit_price=unit, subtotal=round(unit * qty, 2)))
    return CartOut(user_id=user_id, items=items, total=round(sum(i.subtotal for i in items), 2))


def order_doc_to_out(doc: dict) -> OrderOut:
    payment = doc.get("payment")
    return OrderOut(
        id=doc["_id"],
        user_id=doc["user_id"],
        status=doc["status"],
        total=cents_to_amount(doc["total_cents"]),
        created_at=doc["created_at"],
        items=[
            OrderItemOut(product_id=i["product_id"], quantity=i["quantity"], unit_price=cents_to_amount(i["unit_price_cents"]))
            for i in doc["items"]
        ],
        payment=PaymentOut(
            status=payment["status"], provider_ref=payment["provider_ref"], amount=cents_to_amount(payment["amount_cents"])
        )
        if payment
        else None,
    )
