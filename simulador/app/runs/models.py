"""Modelo de una corrida del simulador (lo que se guarda y se muestra)."""
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunEvent(BaseModel):
    """Algo que pasó durante la corrida y se dibuja en la línea de tiempo."""
    system: str | None = None
    t: float | None = None
    kind: str           # phase | kill | restore | info | error
    message: str
    at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SystemResult(BaseModel):
    system: str
    summary: dict = {}
    timeline: list[dict] = []
    consistency: dict | None = None
    stats: dict | None = None
    extra: dict = {}


class Run(BaseModel):
    id: str
    scenario: str
    params: dict
    systems: list[str]
    status: RunStatus = RunStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    events: list[RunEvent] = []
    results: dict[str, SystemResult] = {}
    error: str | None = None
