"""Inyección de fallas: apagar y volver a encender un nodo de base de datos.

Tres implementaciones con la misma interfaz:
    DockerInjector  apaga/enciende un contenedor (usa el socket de Docker)
    ShellInjector   ejecuta los comandos que se configuren
    NoopInjector    no hace nada (escenario deshabilitado)
"""
import asyncio
from abc import ABC, abstractmethod

from app.core.config import Settings


class FailureInjector(ABC):
    description: str

    @property
    def available(self) -> bool:
        return True

    @abstractmethod
    async def kill(self) -> str: ...

    @abstractmethod
    async def restore(self) -> str: ...


class DockerInjector(FailureInjector):
    def __init__(self, container: str):
        self._container = container
        self.description = f"contenedor {container}"

    def _client(self):
        import docker  # import diferido: solo hace falta en este modo

        return docker.from_env()

    @property
    def available(self) -> bool:
        try:
            self._client().containers.get(self._container)
            return True
        except Exception:  # noqa: BLE001 - cualquier fallo = no disponible
            return False

    async def kill(self) -> str:
        # kill (no stop): simula una caída abrupta, sin apagado ordenado
        await asyncio.to_thread(lambda: self._client().containers.get(self._container).kill())
        return f"Se apagó abruptamente {self._container}"

    async def restore(self) -> str:
        await asyncio.to_thread(lambda: self._client().containers.get(self._container).start())
        return f"Se volvió a encender {self._container}"


class ShellInjector(FailureInjector):
    def __init__(self, kill_cmd: str, restore_cmd: str):
        self._kill_cmd, self._restore_cmd = kill_cmd, restore_cmd
        self.description = f"comando: {kill_cmd}"

    @property
    def available(self) -> bool:
        return bool(self._kill_cmd)

    async def _run(self, cmd: str) -> str:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        out, _ = await proc.communicate()
        if proc.returncode == 0:
            return f"Comando ejecutado: {cmd[:90]}"
        return f"El comando falló (código {proc.returncode}): {out.decode(errors='replace').strip()[:160]}"

    async def kill(self) -> str:
        return await self._run(self._kill_cmd)

    async def restore(self) -> str:
        return await self._run(self._restore_cmd) if self._restore_cmd else "Sin comando de recuperación"


class NoopInjector(FailureInjector):
    description = "deshabilitado"

    @property
    def available(self) -> bool:
        return False

    async def kill(self) -> str:
        return "Inyección de fallas deshabilitada"

    async def restore(self) -> str:
        return "Inyección de fallas deshabilitada"


def build_injector(system: str, settings: Settings) -> FailureInjector:
    prefix = f"failover_{system.lower()}_"
    mode = getattr(settings, prefix + "mode")
    if mode == "docker":
        return DockerInjector(getattr(settings, prefix + "container"))
    if mode == "shell":
        return ShellInjector(getattr(settings, prefix + "kill_cmd"), getattr(settings, prefix + "restore_cmd"))
    return NoopInjector()
