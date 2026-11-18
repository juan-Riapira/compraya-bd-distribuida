"""Extracción desde PostgreSQL (Sistema A).

Toda la lectura ocurre dentro de UNA transacción ``REPEATABLE READ READ ONLY``:
el ETL ve una foto consistente de la base aunque la tienda siga vendiendo, y
no bloquea a nadie (en PostgreSQL los lectores no bloquean a los escritores).

Cada consulta trae un agregado completo del modelo destino (producto con su
categoría e inventario, pedido con sus ítems y su pago) y se recorre con un
cursor del lado del servidor, en lotes, para no cargar toda la tabla en memoria.
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg

PRODUCTS_SQL = """
    SELECT p.id, p.name, p.description, p.price, p.created_at,
           c.id AS category_id, c.name AS category_name,
           i.quantity AS stock
    FROM products p
    JOIN categories c ON c.id = p.category_id
    JOIN inventory  i ON i.product_id = p.id
    ORDER BY p.id
"""

USERS_SQL = """
    SELECT id, name, email, country, created_at
    FROM users
    ORDER BY id
"""

# Un pedido normalizado vive en 3 tablas; aquí se reúne en una sola fila.
ORDERS_SQL = """
    SELECT o.id, o.user_id, u.country, o.status, o.total, o.created_at,
           json_agg(json_build_object(
               'product_id', oi.product_id, 'name', p.name,
               'quantity', oi.quantity, 'unit_price', oi.unit_price
           ) ORDER BY oi.product_id) AS items,
           pay.status AS payment_status, pay.provider_ref, pay.amount AS payment_amount
    FROM orders o
    JOIN users u        ON u.id = o.user_id
    JOIN order_items oi ON oi.order_id = o.id
    JOIN products p     ON p.id = oi.product_id
    LEFT JOIN payments pay ON pay.order_id = o.id
    GROUP BY o.id, u.country, pay.status, pay.provider_ref, pay.amount
    ORDER BY o.id
"""

CARTS_SQL = """
    SELECT c.user_id, ci.product_id, ci.quantity
    FROM carts c
    JOIN cart_items ci ON ci.cart_id = c.id
    ORDER BY c.user_id, ci.product_id
"""

# Sumas de control del origen (las usa ``validate``).
CHECKSUMS_SQL = """
    SELECT (SELECT count(*) FROM products)                       AS products,
           (SELECT count(*) FROM users)                          AS users,
           (SELECT count(*) FROM orders)                         AS orders,
           (SELECT coalesce(sum(quantity), 0) FROM inventory)    AS stock_units,
           (SELECT coalesce(sum(round(total * 100)), 0) FROM orders) AS revenue_cents,
           (SELECT count(DISTINCT c.user_id) FROM carts c
              JOIN cart_items ci ON ci.cart_id = c.id)           AS carts
"""


class PostgresExtractor:
    def __init__(self, conn: asyncpg.Connection, batch_size: int):
        self._conn = conn
        self._batch = batch_size

    @classmethod
    @asynccontextmanager
    async def snapshot(cls, dsn: str, batch_size: int) -> AsyncIterator["PostgresExtractor"]:
        conn = await asyncpg.connect(dsn)
        try:
            async with conn.transaction(isolation="repeatable_read", readonly=True):
                yield cls(conn, batch_size)
        finally:
            await conn.close()

    async def _batches(self, sql: str) -> AsyncIterator[list[asyncpg.Record]]:
        cursor = await self._conn.cursor(sql)
        while rows := await cursor.fetch(self._batch):
            yield rows

    def products(self) -> AsyncIterator[list[asyncpg.Record]]:
        return self._batches(PRODUCTS_SQL)

    def users(self) -> AsyncIterator[list[asyncpg.Record]]:
        return self._batches(USERS_SQL)

    def orders(self) -> AsyncIterator[list[asyncpg.Record]]:
        return self._batches(ORDERS_SQL)

    def cart_items(self) -> AsyncIterator[list[asyncpg.Record]]:
        return self._batches(CARTS_SQL)

    async def checksums(self) -> dict[str, int]:
        row = await self._conn.fetchrow(CHECKSUMS_SQL)
        return {k: int(v) for k, v in row.items()}
