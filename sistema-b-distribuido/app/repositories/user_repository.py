"""Acceso a la colección `users`.

Shard key: {_id: "hashed"}. Buscar un usuario por id es una consulta dirigida
a un único shard.
"""
from pymongo.asynchronous.database import AsyncDatabase

from app.db.mongo import USERS


class UserRepository:
    def __init__(self, db: AsyncDatabase):
        self._col = db[USERS]

    async def get(self, user_id: str) -> dict | None:
        return await self._col.find_one({"_id": user_id}, projection={"country": 1, "name": 1})

