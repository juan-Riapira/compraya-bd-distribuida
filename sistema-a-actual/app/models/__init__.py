"""Importa todos los modelos para que queden registrados en `Base.metadata`."""
from app.models.cart import Cart, CartItem
from app.models.catalog import Category, Product
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem, Payment
from app.models.user import User

__all__ = [
    "Cart",
    "CartItem",
    "Category",
    "Inventory",
    "Order",
    "OrderItem",
    "Payment",
    "Product",
    "User",
]
