"""Configuración central del Sistema A.

Única fuente de verdad para variables de entorno. Ningún otro módulo
lee `os.environ` directamente: todos piden `get_settings()`.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CompraYa · Sistema actual (PostgreSQL monolítico)"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    admin_enabled: bool = True  # /admin/* (reinicio y métricas para el simulador)
    deal_count: int = 20        # P00001..P000NN son las "ofertas del día"

    @property
    def deal_product_ids(self) -> list[str]:
        return [f"P{i:05d}" for i in range(1, self.deal_count + 1)]

    # --- Base de datos (un único servidor PostgreSQL) ---
    database_url: str = "postgresql+asyncpg://compraya:compraya@localhost:5432/compraya"
    db_pool_size: int = 10
    db_max_overflow: int = 10
    db_pool_timeout_s: float = 10.0

    # --- Pasarela de pago simulada ---
    payment_latency_ms: int = 80
    payment_failure_rate: float = 0.02


@lru_cache
def get_settings() -> Settings:
    return Settings()
