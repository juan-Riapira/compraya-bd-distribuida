"""Existencias "calientes" en Redis: `stock:{product_id}` -> unidades disponibles.

Redis actúa como compuerta rápida para el checkout: la reserva de TODOS los
productos del carrito se hace en un script Lua que Redis ejecuta de forma
atómica (nadie más corre en medio). Así no hay bloqueos de fila ni esperas,
y nunca se vende más de lo que hay. MongoDB sigue siendo la fuente de verdad
y confirma el descuento dentro de su transacción.
"""
from redis.asyncio import Redis

from app.db import keys

# Devuelve 0 si reservó todo; i (1-based) si el ítem i no alcanza;
# -i si la llave del ítem i no existe todavía (hay que calentarla).
_RESERVE_LUA = """
for i, key in ipairs(KEYS) do
    local current = redis.call('GET', key)
    if not current then return -i end
    if tonumber(current) < tonumber(ARGV[i]) then return i end
end
for i, key in ipairs(KEYS) do
    redis.call('DECRBY', key, ARGV[i])
end
return 0
"""


class StockReservationError(Exception):
    def __init__(self, product_id: str):
        super().__init__(product_id)
        self.product_id = product_id


class MissingStockKeyError(StockReservationError):
    pass


class StockRepository:
    def __init__(self, redis: Redis):
        self._redis = redis
        self._reserve = redis.register_script(_RESERVE_LUA)

    async def get_many(self, product_ids: list[str]) -> dict[str, int | None]:
        if not product_ids:
            return {}
        values = await self._redis.mget([keys.stock(p) for p in product_ids])
        return {pid: (int(v) if v is not None else None) for pid, v in zip(product_ids, values)}

    async def warm(self, stock_by_product: dict[str, int]) -> None:
        """Carga existencias desde MongoDB sin pisar valores ya presentes (SET NX)."""
        async with self._redis.pipeline(transaction=False) as pipe:
            for pid, qty in stock_by_product.items():
                pipe.set(keys.stock(pid), qty, nx=True)
            await pipe.execute()

    async def overwrite(self, stock_by_product: dict[str, int]) -> None:
        """Reemplaza existencias (usado por la siembra y la reconciliación)."""
        if stock_by_product:
            await self._redis.mset({keys.stock(p): q for p, q in stock_by_product.items()})

    async def reserve(self, items: dict[str, int]) -> None:
        product_ids = sorted(items)
        result = int(
            await self._reserve(keys=[keys.stock(p) for p in product_ids], args=[items[p] for p in product_ids])
        )
        if result == 0:
            return
        if result < 0:
            raise MissingStockKeyError(product_ids[-result - 1])
        raise StockReservationError(product_ids[result - 1])

    async def release(self, items: dict[str, int]) -> None:
        async with self._redis.pipeline(transaction=True) as pipe:
            for pid, qty in items.items():
                pipe.incrby(keys.stock(pid), qty)
            await pipe.execute()
