"""Inyección de dependencias: arma repositorios y servicios por petición.

Es el único lugar donde se "cablea" la aplicación; las rutas solo piden el
servicio que necesitan y no conocen la base de datos.
"""
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import engine, get_session
from app.integrations.payment_gateway import PaymentGateway
from app.repositories.admin_repository import AdminRepository
from app.repositories.cart_repository import CartRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.services.admin_service import AdminService
from app.services.cart_service import CartService
from app.services.catalog_service import CatalogService
from app.services.checkout_service import CheckoutService
from app.services.order_service import OrderService
from app.services.user_service import UserService


@lru_cache
def get_payment_gateway() -> PaymentGateway:
    s = get_settings()
    return PaymentGateway(latency_ms=s.payment_latency_ms, failure_rate=s.payment_failure_rate)


def get_catalog_service(session: AsyncSession = Depends(get_session)) -> CatalogService:
    return CatalogService(ProductRepository(session), get_settings().deal_product_ids)


def get_cart_service(session: AsyncSession = Depends(get_session)) -> CartService:
    return CartService(session, CartRepository(session), ProductRepository(session), UserRepository(session))


def get_checkout_service(
    session: AsyncSession = Depends(get_session),
    gateway: PaymentGateway = Depends(get_payment_gateway),
) -> CheckoutService:
    return CheckoutService(
        session, CartRepository(session), InventoryRepository(session), OrderRepository(session), gateway
    )


def get_order_service(session: AsyncSession = Depends(get_session)) -> OrderService:
    return OrderService(OrderRepository(session))


def get_admin_service(session: AsyncSession = Depends(get_session)) -> AdminService:
    return AdminService(engine, AdminRepository(session))


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(UserRepository(session))
