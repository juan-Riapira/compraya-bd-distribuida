"""Carga del dataset en PostgreSQL (recrea el esquema desde cero).

La usan el script `python -m scripts.seed` y el endpoint `POST /admin/reset`
que llama el simulador antes de cada prueba.
"""
from decimal import Decimal

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.base import Base
from app.models import Category, Inventory, Product, User
from app.seed.dataset import build_dataset

BATCH = 1000


async def seed_database(engine: AsyncEngine) -> dict:
    categories, products, users = build_dataset()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

        await conn.execute(insert(Category), [{"id": c.id, "name": c.name} for c in categories])
        product_rows = [
            {"id": p.id, "name": p.name, "description": p.description,
             "price": Decimal(str(p.price)), "category_id": p.category_id}
            for p in products
        ]
        inventory_rows = [{"product_id": p.id, "quantity": p.stock} for p in products]
        user_rows = [{"id": u.id, "name": u.name, "email": u.email, "country": u.country} for u in users]

        for table, rows in ((Product, product_rows), (Inventory, inventory_rows), (User, user_rows)):
            for i in range(0, len(rows), BATCH):
                await conn.execute(insert(table), rows[i : i + BATCH])

    return {"categories": len(categories), "products": len(products), "users": len(users)}
