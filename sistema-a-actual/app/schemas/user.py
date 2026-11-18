"""Contrato público de usuarios (idéntico en el Sistema A y el B)."""
from pydantic import BaseModel


class UserOut(BaseModel):
    id: str
    name: str
    country: str
