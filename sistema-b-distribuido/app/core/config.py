"""Configuración central del Sistema B.

Única fuente de verdad para variables de entorno. Ningún otro módulo
lee `os.environ` directamente: todos piden `get_settings()`.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CompraYa · Sistema propuesto (MongoDB sharded + Redis)"
    api_prefix: str = "/api/v1"
    instance_id: str = "api-local"
    log_level: str = "INFO"
    admin_enabled: bool = True  # /admin/* (reinicio y métricas para el simulador)
    deal_count: int = 20        # P00001..P000NN son las "ofertas del día"

    @property
    def deal_product_ids(self) -> list[str]:
        return [f"P{i:05d}" for i in range(1, self.deal_count + 1)]

    # --- MongoDB: la API habla con el router `mongos`, nunca con un shard ---
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "compraya"
    mongo_max_pool_size: int = 50

    # --- Redis: caché, carritos, existencias calientes e idempotencia ---
    redis_url: str = "redis://localhost:6379/0"
    product_cache_ttl_s: int = 300
    list_cache_ttl_s: int = 30
    cart_ttl_s: int = 7 * 24 * 3600
    idempotency_ttl_s: int = 24 * 3600

    # --- Pasarela de pago simulada (idéntica al Sistema A) ---
    payment_latency_ms: int = 80
    payment_failure_rate: float = 0.02


@lru_cache
def get_settings() -> Settings:
    return Settings()
