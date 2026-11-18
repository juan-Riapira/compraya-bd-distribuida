"""Conexión a Redis (capa en memoria del Sistema B)."""
from redis.asyncio import Redis

from app.core.config import Settings


class RedisConnection:
    def __init__(self, settings: Settings):
        self._client: Redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            health_check_interval=30,
            max_connections=200,
        )

    @property
    def client(self) -> Redis:
        return self._client

    async def ping(self) -> None:
        await self._client.ping()

    async def close(self) -> None:
        await self._client.aclose()
