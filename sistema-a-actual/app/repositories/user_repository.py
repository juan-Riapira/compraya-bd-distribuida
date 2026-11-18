"""Acceso a datos de usuarios."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def exists(self, user_id: str) -> bool:
        return await self._session.get(User, user_id) is not None

    async def get(self, user_id: str) -> User | None:
        return await self._session.get(User, user_id)
