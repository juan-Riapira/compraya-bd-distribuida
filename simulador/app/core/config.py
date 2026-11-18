"""Configuración del simulador (única fuente de variables de entorno)."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

FailureMode = Literal["docker", "shell", "none"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    log_level: str = "INFO"
    data_dir: Path = Path("data")

    # --- Sistemas a probar ---
    target_a_url: str = "http://localhost:8001"
    target_b_url: str = "http://localhost:8002"
    # URL que abre el NAVEGADOR (cuando el simulador corre en Docker difiere de la interna)
    target_a_public_url: str = ""
    target_b_public_url: str = ""

    # --- Inyección de fallas (escenario "caída de un nodo") ---
    # docker: apaga/enciende un contenedor por nombre (requiere el socket de Docker)
    # shell:  ejecuta comandos arbitrarios · none: escenario deshabilitado
    failover_a_mode: FailureMode = "docker"
    failover_a_container: str = "compraya-sistema-a-postgres-1"
    failover_a_kill_cmd: str = ""
    failover_a_restore_cmd: str = ""

    failover_b_mode: FailureMode = "docker"
    failover_b_container: str = "compraya-sistema-b-shard1-a-1"
    failover_b_kill_cmd: str = ""
    failover_b_restore_cmd: str = ""

    # --- Límites de seguridad para no tumbar el equipo del estudiante ---
    max_virtual_users: int = 600
    max_duration_s: int = 300
    request_timeout_s: float = 15.0

    def target_url(self, system: str) -> str:
        return self.target_a_url if system == "A" else self.target_b_url

    def public_url(self, system: str) -> str:
        public = self.target_a_public_url if system == "A" else self.target_b_public_url
        return public or self.target_url(system)


@lru_cache
def get_settings() -> Settings:
    return Settings()
