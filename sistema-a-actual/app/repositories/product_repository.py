"""Acceso a datos del catálogo (products + categories + inventory)."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Product


class ProductRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_page(self, limit: int, offset: int, category: str | None = None) -> list[Product]:
        # JOIN products-categories-inventory + paginación por OFFSET en cada
        # visita al catálogo: nada se cachea, todo golpea al servidor único.
        stmt = select(Product).order_by(Product.name, Product.id).limit(limit).offset(offset)
        if category:
            stmt = stmt.join(Product.category).where(Category.name == category)
        result = await self._session.execute(stmt)
        return list(result.unique().scalars())

    async def get(self, product_id: str) -> Product | None:
        return await self._session.get(Product, product_id)

    async def get_many(self, product_ids: list[str]) -> dict[str, Product]:
        result = await self._session.execute(select(Product).where(Product.id.in_(product_ids)))
        return {p.id: p for p in result.unique().scalars()}

    async def list_categories(self) -> list[str]:
        result = await self._session.execute(select(Category.name).order_by(Category.name))
        return list(result.scalars())
