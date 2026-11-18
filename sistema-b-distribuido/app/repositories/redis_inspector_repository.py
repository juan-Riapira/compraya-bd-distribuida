"""Lectura de solo consulta de las llaves de Redis (para el panel de demostración).

Usa SCAN (no KEYS) para no bloquear Redis mientras recorre las llaves, y
pipelines para pedir tipo, TTL y valor de muchas llaves en un solo viaje.
"""
import json

from redis.asyncio import Redis

_PREVIEW_CHARS = 220


class RedisInspectorRepository:
    def __init__(self, redis: Redis):
        self._redis = redis

    async def keys(self, pattern: str) -> list[str]:
        return sorted([k async for k in self._redis.scan_iter(match=pattern, count=1000)])

    async def count(self, pattern: str) -> int:
        n = 0
        async for _ in self._redis.scan_iter(match=pattern, count=1000):
            n += 1
        return n

    async def describe(self, keys: list[str]) -> list[dict]:
        """Tipo, segundos de vida restantes (-1 = sin vencimiento) y vista previa del valor."""
        if not keys:
            return []
        async with self._redis.pipeline(transaction=False) as pipe:
            for k in keys:
                pipe.type(k)
                pipe.ttl(k)
            meta = await pipe.execute()
        types, ttls = meta[0::2], meta[1::2]

        async with self._redis.pipeline(transaction=False) as pipe:
            for k, t in zip(keys, types):
                if t == "hash":
                    pipe.hgetall(k)
                elif t == "string":
                    pipe.get(k)
                else:  # tipo sin vista previa: se pide algo barato para no desalinear la lista
                    pipe.exists(k)
            values = await pipe.execute()

        out = []
        for k, t, ttl, v in zip(keys, types, ttls, values):
            if t == "none":  # expiró entre el SCAN y la lectura
                continue
            preview = _readable(v) if t in ("hash", "string") else ""
            out.append({
                "key": k,
                "type": t,
                "ttl_s": int(ttl),
                "preview": preview[:_PREVIEW_CHARS] + ("…" if len(preview) > _PREVIEW_CHARS else ""),
            })
        return out

    async def delete_matching(self, pattern: str) -> int:
        batch, deleted = [], 0
        async for k in self._redis.scan_iter(match=pattern, count=1000):
            batch.append(k)
            if len(batch) == 500:
                deleted += await self._redis.unlink(*batch)
                batch.clear()
        if batch:
            deleted += await self._redis.unlink(*batch)
        return deleted


def _readable(value) -> str:
    """Muestra JSON y HASH con tildes legibles (sin escapes \\u00e1)."""
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    try:
        return json.dumps(json.loads(value), ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)
