"""Casos de uso del catálogo con caché *cache-aside*.

Lectura: Redis primero -> si falla, MongoDB -> se guarda en Redis.
En Black Friday más del 90 % de las visitas al catálogo se resuelven en
memoria y no llegan a la base de datos.
"""
from app.cache.product_cache import ProductCache
from app.core.exceptions import NotFoundError
from app.repositories.product_repository import ProductRepository
from app.repositories.stock_repository import StockRepository
from app.schemas.product import ProductOut, ProductPage
from app.services.mappers import product_doc_to_static, static_to_out


class CatalogService:
    def __init__(self, products: ProductRepository, cache: ProductCache, stock: StockRepository, deal_ids: list[str]):
        self._deal_ids = deal_ids
        self._products = products
        self._cache = cache
        self._stock = stock

    async def list_products(self, limit: int, offset: int, category: str | None) -> ProductPage:
        statics = await self._cache.get_list(category, limit, offset)
        if statics is None:
            docs = await self._products.list_page(limit, offset, category)
            statics = [product_doc_to_static(d) for d in docs]
            await self._cache.set_list(category, limit, offset, statics)
            await self._stock.warm({d["_id"]: d["stock"] for d in docs})
        stock = await self._stock_for([s["id"] for s in statics])
        return ProductPage(items=[static_to_out(s, stock[s["id"]]) for s in statics], limit=limit, offset=offset)

    async def get_product(self, product_id: str) -> ProductOut:
        statics = await self.get_static_many([product_id])
        if product_id not in statics:
            raise NotFoundError(f"Producto {product_id} no existe")
        stock = await self._stock_for([product_id])
        return static_to_out(statics[product_id], stock[product_id])

    async def get_static_many(self, product_ids: list[str]) -> dict[str, dict]:
        """Datos estáticos (nombre, precio...) de varios productos, desde caché o MongoDB."""
        found = await self._cache.get_many(product_ids)
        missing = [p for p in product_ids if p not in found]
        if missing:
            docs = await self._products.get_many(missing)
            fresh = [product_doc_to_static(d) for d in docs.values()]
            await self._cache.set_many(fresh)
            await self._stock.warm({pid: d["stock"] for pid, d in docs.items()})
            found.update({s["id"]: s for s in fresh})
        return found

    async def _stock_for(self, product_ids: list[str]) -> dict[str, int]:
        stock = await self._stock.get_many(product_ids)
        missing = [p for p, v in stock.items() if v is None]
        if missing:
            docs = await self._products.get_many(missing)
            from_db = {pid: d["stock"] for pid, d in docs.items()}
            await self._stock.warm(from_db)
            stock.update(from_db)
        return {p: (v or 0) for p, v in stock.items()}

    async def list_categories(self) -> list[str]:
        return await self._products.list_categories()

    async def list_deals(self) -> list[ProductOut]:
        statics = await self.get_static_many(self._deal_ids)
        stock = await self._stock_for([pid for pid in self._deal_ids if pid in statics])
        return [static_to_out(statics[pid], stock[pid]) for pid in self._deal_ids if pid in statics]
