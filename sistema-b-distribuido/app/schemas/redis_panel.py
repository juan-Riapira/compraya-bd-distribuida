"""Contrato del panel de Redis (solo existe en el Sistema B)."""
from pydantic import BaseModel


class RedisKeyOut(BaseModel):
    key: str
    type: str
    ttl_s: int          # segundos de vida restantes; -1 = no vence
    preview: str


class RedisGroupOut(BaseModel):
    id: str
    pattern: str
    purpose: str
    clearable: bool
    configured_ttl_s: int | None
    count: int


class RedisPanelOut(BaseModel):
    group: str
    groups: list[RedisGroupOut]
    keys: list[RedisKeyOut]
