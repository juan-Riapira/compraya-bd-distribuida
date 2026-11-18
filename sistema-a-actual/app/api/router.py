"""Agrupa todas las rutas versionadas bajo /api/v1."""
from fastapi import APIRouter

from app.api.routes import carts, orders, products, users

api_router = APIRouter()
api_router.include_router(products.router)
api_router.include_router(carts.router)
api_router.include_router(orders.router)
api_router.include_router(users.router)
