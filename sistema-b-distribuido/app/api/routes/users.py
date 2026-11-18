"""Rutas HTTP de usuarios."""
from fastapi import APIRouter, Depends

from app.api.deps import get_user_service
from app.schemas.user import UserOut
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["usuarios"])


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: str, service: UserService = Depends(get_user_service)) -> UserOut:
    return await service.get_user(user_id)
