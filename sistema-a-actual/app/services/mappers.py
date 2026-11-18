"""Traducción de entidades ORM a los DTO públicos (schemas)."""
from app.models import Cart, Order, Product
from app.schemas.cart import CartItemOut, CartOut
from app.schemas.order import OrderItemOut, OrderOut, PaymentOut
from app.schemas.product import ProductOut


def product_to_out(product: Product) -> ProductOut:
    return ProductOut(
        id=product.id,
        name=product.name,
        description=product.description,
        price=float(product.price),
        category=product.category.name,
        stock=product.inventory.quantity if product.inventory else 0,
    )


def cart_to_out(user_id: str, cart: Cart | None) -> CartOut:
    items = [
        CartItemOut(
            product_id=i.product_id,
            quantity=i.quantity,
            unit_price=float(i.unit_price),
            subtotal=round(float(i.unit_price) * i.quantity, 2),
        )
        for i in (cart.items if cart else [])
    ]
    return CartOut(user_id=user_id, items=items, total=round(sum(i.subtotal for i in items), 2))


def order_to_out(order: Order) -> OrderOut:
    payment = (
        PaymentOut(status=order.payment.status, provider_ref=order.payment.provider_ref, amount=float(order.payment.amount))
        if order.payment
        else None
    )
    return OrderOut(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        total=float(order.total),
        created_at=order.created_at,
        items=[
            OrderItemOut(product_id=i.product_id, quantity=i.quantity, unit_price=float(i.unit_price))
            for i in order.items
        ],
        payment=payment,
    )
