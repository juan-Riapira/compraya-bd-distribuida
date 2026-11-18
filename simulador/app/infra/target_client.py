"""Cliente de los endpoints de administración de cada sistema (A o B)."""
import httpx


class TargetClient:
    def __init__(self, system: str, base_url: str):
        self.system = system
        self.base_url = base_url.rstrip("/")

    async def _get(self, path: str, timeout: float = 10) -> dict:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout) as c:
            r = await c.get(path)
            r.raise_for_status()
            return r.json()

    async def health(self) -> dict:
        try:
            return {"online": True, **(await self._get("/health", timeout=3))}
        except (httpx.HTTPError, ValueError) as exc:
            return {"online": False, "system": self.system, "error": type(exc).__name__}

    async def reset(self) -> dict:
        async with httpx.AsyncClient(base_url=self.base_url, timeout=120) as c:
            r = await c.post("/admin/reset")
            r.raise_for_status()
            return r.json()

    async def stats(self) -> dict:
        return await self._get("/admin/stats")

    async def consistency(self) -> dict:
        return await self._get("/admin/consistency", timeout=60)
