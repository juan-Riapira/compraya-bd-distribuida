"""Crea el esquema y carga el dataset en PostgreSQL.

Uso:  python -m scripts.seed
"""
import asyncio

from app.db.session import engine
from app.seed.loader import seed_database


async def main() -> None:
    result = await seed_database(engine)
    await engine.dispose()
    print(f"Sistema A sembrado: {result['categories']} categorías, {result['products']} productos, {result['users']} usuarios")


if __name__ == "__main__":
    asyncio.run(main())
