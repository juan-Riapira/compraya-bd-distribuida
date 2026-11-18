"""Casos de uso del catálogo: listar y consultar productos."""
from app.core.exceptions import NotFoundError
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductOut, ProductPage
from app.services.mappers import product_to_out


class CatalogService:
    def __init__(self, products: ProductRepository, deal_ids: list[str]):
        self._products = products
        self._deal_ids = deal_ids

    async def list_products(self, limit: int, offset: int, category: str | None) -> ProductPage:
        products = await self._products.list_page(limit=limit, offset=offset, category=category)
        return ProductPage(items=[product_to_out(p) for p in products], limit=limit, offset=offset)

    async def get_product(self, product_id: str) -> ProductOut:
        product = await self._products.get(product_id)
        if product is None:
            raise NotFoundError(f"Producto {product_id} no existe")
        return product_to_out(product)

    async def list_categories(self) -> list[str]:
        return await self._products.list_categories()

    async def list_deals(self) -> list[ProductOut]:
        products = await self._products.get_many(self._deal_ids)
        return [product_to_out(products[pid]) for pid in self._deal_ids if pid in products]
