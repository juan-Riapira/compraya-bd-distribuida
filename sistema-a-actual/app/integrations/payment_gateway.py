"""Pasarela de pago simulada.

Imita a un proveedor externo: tarda `payment_latency_ms` y rechaza un
porcentaje de cobros. Es la MISMA implementación en ambos sistemas para que
la comparación sea justa; lo que cambia es *dónde* se la invoca.
"""
import asyncio
import random
import uuid
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PaymentResult:
    approved: bool
    provider_ref: str


class PaymentGateway:
    def __init__(self, latency_ms: int, failure_rate: float):
        self._latency_s = latency_ms / 1000
        self._failure_rate = failure_rate

    async def charge(self, order_id: str, amount: Decimal) -> PaymentResult:
        await asyncio.sleep(self._latency_s)
        approved = random.random() >= self._failure_rate
        return PaymentResult(approved=approved, provider_ref=f"pay_{uuid.uuid4().hex[:16]}")

    async def refund(self, provider_ref: str) -> None:
        """Reembolso simulado (en el Sistema A nunca se invoca: un fallo tras cobrar deja el dinero cobrado)."""
        await asyncio.sleep(self._latency_s)
