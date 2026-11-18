"""Recolección de métricas por segundo y resumen final de una corrida.

Cada petición registra: endpoint, latencia y resultado. Las latencias se miden
solo sobre peticiones RESPONDIDAS (una falla instantánea no debe "mejorar" la
latencia). Los resultados se clasifican en tres grupos:
    ok        2xx
    business  400 carrito vacío · 402 pago rechazado · 409 agotado   (NO es falla técnica)
    failure   5xx, timeouts y errores de conexión                    (falla técnica)
"""
import time
from collections import defaultdict
from dataclasses import dataclass, field

BUSINESS_STATUSES = {400, 402, 409}


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def classify(status: int | None) -> str:
    if status is not None and 200 <= status < 300:
        return "ok"
    if status in BUSINESS_STATUSES:
        return "business"
    return "failure"


@dataclass
class _Bucket:
    latencies: list[float] = field(default_factory=list)
    ok: int = 0
    business: int = 0
    failure: int = 0
    checkouts_ok: int = 0


class MetricsCollector:
    """Acumula muestras de una corrida contra UN sistema."""

    def __init__(self) -> None:
        self.started = time.perf_counter()
        self._buckets: dict[int, _Bucket] = defaultdict(_Bucket)
        self._by_endpoint: dict[str, list[float]] = defaultdict(list)
        self._all: list[float] = []
        self.totals = {"ok": 0, "business": 0, "failure": 0, "checkouts_ok": 0}
        self.status_counts: dict[str, int] = defaultdict(int)

    def elapsed(self) -> float:
        return time.perf_counter() - self.started

    def record(self, endpoint: str, latency_ms: float, status: int | None) -> None:
        kind = classify(status)
        bucket = self._buckets[int(self.elapsed())]
        setattr(bucket, kind, getattr(bucket, kind) + 1)
        self.totals[kind] += 1
        self.status_counts[str(status or "error")] += 1
        if endpoint == "checkout" and kind == "ok":
            bucket.checkouts_ok += 1
            self.totals["checkouts_ok"] += 1
        if kind != "failure":
            bucket.latencies.append(latency_ms)
            self._by_endpoint[endpoint].append(latency_ms)
            self._all.append(latency_ms)

    def second(self, sec: int) -> dict:
        """Métricas de un segundo ya cerrado (para la gráfica en vivo)."""
        b = self._buckets.get(sec, _Bucket())
        return {
            "t": sec,
            "rps": b.ok + b.business,          # peticiones respondidas en ese segundo
            "ok": b.ok,
            "business": b.business,
            "failures": b.failure,
            "checkouts": b.checkouts_ok,
            "p50": round(percentile(b.latencies, 50), 1),
            "p95": round(percentile(b.latencies, 95), 1),
        }

    def summary(self) -> dict:
        duration = max(self.elapsed(), 0.001)
        served = len(self._all)
        total = served + self.totals["failure"]
        return {
            "requests": total,
            "served": served,
            "duration_s": round(duration, 1),
            "rps": round(served / duration, 1),
            "p50_ms": round(percentile(self._all, 50)),
            "p95_ms": round(percentile(self._all, 95)),
            "p99_ms": round(percentile(self._all, 99)),
            "max_ms": round(max(self._all, default=0)),
            "ok": self.totals["ok"],
            "business": self.totals["business"],
            "failures": self.totals["failure"],
            "failure_rate": round(self.totals["failure"] / total * 100, 2) if total else 0.0,
            "checkouts_ok": self.totals["checkouts_ok"],
            "endpoints": {
                name: {"count": len(v), "p50_ms": round(percentile(v, 50)), "p95_ms": round(percentile(v, 95))}
                for name, v in sorted(self._by_endpoint.items())
            },
            "status_counts": dict(self.status_counts),
        }
