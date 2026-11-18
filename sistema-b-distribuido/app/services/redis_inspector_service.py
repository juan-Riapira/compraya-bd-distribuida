"""Panel de Redis: qué guarda el Sistema B en memoria y cuánto tiempo le queda a cada dato.

Solo deja ver los grupos de llaves conocidos (``app/db/keys.py``) y solo
permite borrar la caché del catálogo, que se reconstruye sola (cache-aside).
"""
from app.core.config import Settings
from app.repositories.redis_inspector_repository import RedisInspectorRepository
from app.schemas.redis_panel import RedisGroupOut, RedisKeyOut, RedisPanelOut

# grupo -> (patrón de llaves, para qué sirve, ¿es caché que se puede vaciar?)
GROUPS: dict[str, tuple[str, str, bool]] = {
    "product": ("product:*", "Caché de cada producto (cache-aside)", True),
    "list": ("products:list:*", "Caché de páginas del catálogo", True),
    "stock": ("stock:*", "Stock en caliente (reserva atómica Lua)", False),
    "cart": ("cart:*", "Carritos de compra (HASH)", False),
    "idem": ("idem:*", "Llaves de idempotencia del pago", False),
}


class UnknownGroupError(ValueError):
    pass


class RedisInspectorService:
    def __init__(self, repo: RedisInspectorRepository, settings: Settings):
        self._repo = repo
        self._configured_ttl = {
            "product": settings.product_cache_ttl_s,
            "list": settings.list_cache_ttl_s,
            "stock": None,
            "cart": settings.cart_ttl_s,
            "idem": settings.idempotency_ttl_s,
        }

    async def snapshot(self, group: str, limit: int) -> RedisPanelOut:
        if group not in GROUPS:
            raise UnknownGroupError(group)
        groups = [
            RedisGroupOut(
                id=gid, pattern=pattern, purpose=purpose, clearable=clearable,
                configured_ttl_s=self._configured_ttl[gid], count=await self._repo.count(pattern),
            )
            for gid, (pattern, purpose, clearable) in GROUPS.items()
        ]
        keys = (await self._repo.keys(GROUPS[group][0]))[:limit]
        rows = [RedisKeyOut(**r) for r in await self._repo.describe(keys)]
        return RedisPanelOut(group=group, groups=groups, keys=rows)

    async def clear_catalog_cache(self) -> int:
        return sum([await self._repo.delete_matching(GROUPS[g][0]) for g in ("product", "list")])
