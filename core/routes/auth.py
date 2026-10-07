from fastapi import APIRouter

from core.domain.auth_model import CurrentUser
from core.services.auth import AuthenticatedUser


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me", response_model=CurrentUser)
def get_me(user: AuthenticatedUser) -> CurrentUser:
    return user