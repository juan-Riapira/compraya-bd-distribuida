"""Inyección de dependencias: arma repositorios y servicios por petición.

Las conexiones (MongoDB y Redis) se crean UNA vez al arrancar y viven en
`app.state`; aquí solo se componen los objetos livianos que las usan.
"""
from functools import lru_cache

from fastapi import Depends, Request
from pymongo.asynchronous.database import AsyncDatabase
from redis.asyncio import Redis

from app.cache.product_cache import ProductCache
from app.core.config import Settings, get_settings
from app.db.mongo import MongoConnection
from app.db.redis import RedisConnection
from app.integrations.payment_gateway import PaymentGateway
from app.repositories.admin_repository import AdminRepository
from app.repositories.cart_repository import CartRepository
from app.repositories.idempotency_repository import IdempotencyRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.redis_inspector_repository import RedisInspectorRepository
from app.repositories.stock_repository import StockRepository
from app.repositories.user_repository import UserRepository
from app.services.admin_service import AdminService
from app.services.cart_service import CartService
from app.services.catalog_service import CatalogService
from app.services.checkout_service import CheckoutService
from app.services.order_service import OrderService
from app.services.redis_inspector_service import RedisInspectorService
from app.services.user_service import UserService


# --- Conexiones compartidas -------------------------------------------------
def get_mongo(request: Request) -> MongoConnection:
    return request.app.state.mongo


def get_db(mongo: MongoConnection = Depends(get_mongo)) -> AsyncDatabase:
    return mongo.db


def get_redis(request: Request) -> Redis:
    conn: RedisConnection = request.app.state.redis
    return conn.client


@lru_cache
def get_payment_gateway() -> PaymentGateway:
    s = get_settings()
    return PaymentGateway(latency_ms=s.payment_latency_ms, failure_rate=s.payment_failure_rate)


# --- Servicios --------------------------------------------------------------
def get_catalog_service(
    db: AsyncDatabase = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> CatalogService:
    return CatalogService(
        ProductRepository(db),
        ProductCache(redis, settings.product_cache_ttl_s, settings.list_cache_ttl_s),
        StockRepository(redis),
        settings.deal_product_ids,
    )


def get_cart_service(
    db: AsyncDatabase = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
    catalog: CatalogService = Depends(get_catalog_service),
) -> CartService:
    return CartService(CartRepository(redis, settings.cart_ttl_s), UserRepository(db), catalog)


def get_checkout_service(
    db: AsyncDatabase = Depends(get_db),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
    catalog: CatalogService = Depends(get_catalog_service),
    gateway: PaymentGateway = Depends(get_payment_gateway),
) -> CheckoutService:
    return CheckoutService(
        users=UserRepository(db),
        products=ProductRepository(db),
        orders=OrderRepository(db),
        carts=CartRepository(redis, settings.cart_ttl_s),
        stock=StockRepository(redis),
        idempotency=IdempotencyRepository(redis, settings.idempotency_ttl_s),
        catalog=catalog,
        gateway=gateway,
    )


def get_order_service(db: AsyncDatabase = Depends(get_db)) -> OrderService:
    return OrderService(OrderRepository(db), UserRepository(db))


def get_user_service(db: AsyncDatabase = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db))


def get_admin_service(db: AsyncDatabase = Depends(get_db), redis: Redis = Depends(get_redis)) -> AdminService:
    return AdminService(db, redis, AdminRepository(db), StockRepository(redis))


def get_redis_inspector_service(
    redis: Redis = Depends(get_redis), settings: Settings = Depends(get_settings)
) -> RedisInspectorService:
    return RedisInspectorService(RedisInspectorRepository(redis), settings)
