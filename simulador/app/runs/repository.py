"""Guarda cada corrida como un archivo JSON en data/runs/ (historial)."""
from pathlib import Path

from app.runs.models import Run


class RunRepository:
    def __init__(self, directory: Path):
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, run: Run) -> None:
        (self._dir / f"{run.id}.json").write_text(run.model_dump_json(indent=1), encoding="utf-8")

    def get(self, run_id: str) -> Run | None:
        path = self._dir / f"{run_id}.json"
        return Run.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None

    def list(self, limit: int = 30) -> list[Run]:
        files = sorted(self._dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
        return [Run.model_validate_json(f.read_text(encoding="utf-8")) for f in files]

    def delete(self, run_id: str) -> bool:
        path = self._dir / f"{run_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
