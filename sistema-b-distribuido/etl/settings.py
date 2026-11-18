"""Configuración del ETL (solo lo que no está ya en ``app.core.config``)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class EtlSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ETL_", extra="ignore")

    # Base de datos del Sistema A (origen). Se abre en modo solo lectura.
    source_dsn: str = "postgresql://compraya:compraya@localhost:5432/compraya"
    # Filas por lote: acota la memoria y el tamaño de cada escritura masiva.
    batch_size: int = 1000
    # Si es True, borra el destino antes de cargar (migración inicial "en limpio").
    truncate_target: bool = False


@lru_cache
def get_etl_settings() -> EtlSettings:
    return EtlSettings()
