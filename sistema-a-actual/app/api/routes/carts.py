"""Rutas HTTP del carrito."""
from fastapi import APIRouter, Depends

from app.api.deps import get_cart_service
from app.schemas.cart import CartItemIn, CartOut
from app.services.cart_service import CartService

router = APIRouter(prefix="/carts", tags=["carrito"])


@router.get("/{user_id}", response_model=CartOut)
async def get_cart(user_id: str, service: CartService = Depends(get_cart_service)) -> CartOut:
    return await service.get_cart(user_id)


@router.post("/{user_id}/items", response_model=CartOut, status_code=201)
async def add_item(user_id: str, item: CartItemIn, service: CartService = Depends(get_cart_service)) -> CartOut:
    return await service.add_item(user_id, item)


@router.delete("/{user_id}/items/{product_id}", response_model=CartOut)
async def remove_item(user_id: str, product_id: str, service: CartService = Depends(get_cart_service)) -> CartOut:
    return await service.remove_item(user_id, product_id)
