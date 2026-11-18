"""Consulta de clientes (la usa la tienda web para mostrar quién compra)."""
from app.core.exceptions import NotFoundError
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserOut


class UserService:
    def __init__(self, users: UserRepository):
        self._users = users

    async def get_user(self, user_id: str) -> UserOut:
        user = await self._users.get(user_id)
        if user is None:
            raise NotFoundError(f"Usuario {user_id} no existe")
        return UserOut(id=user["_id"], name=user["name"], country=user["country"])
