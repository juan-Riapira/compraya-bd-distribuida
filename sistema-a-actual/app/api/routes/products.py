"""Rutas HTTP del catálogo."""
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_catalog_service
from app.schemas.product import ProductOut, ProductPage
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/products", tags=["catálogo"])


@router.get("", response_model=ProductPage)
async def list_products(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: str | None = None,
    service: CatalogService = Depends(get_catalog_service),
) -> ProductPage:
    return await service.list_products(limit, offset, category)


@router.get("/deals", response_model=list[ProductOut])
async def list_deals(service: CatalogService = Depends(get_catalog_service)) -> list[ProductOut]:
    """Ofertas del día: los productos que concentran el tráfico en Black Friday."""
    return await service.list_deals()


@router.get("/categories", response_model=list[str])
async def list_categories(service: CatalogService = Depends(get_catalog_service)) -> list[str]:
    return await service.list_categories()


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: str, service: CatalogService = Depends(get_catalog_service)) -> ProductOut:
    return await service.get_product(product_id)
