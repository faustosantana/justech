from fastapi import APIRouter, Request

from app.api.deps import DbSession
from app.core.exceptions import JAIOSException, unauthorized
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: UserCreate, db: DbSession) -> UserResponse:
    service = AuthService(db)
    try:
        user = await service.register_user(data)
        return UserResponse.model_validate(user)
    except JAIOSException as exc:
        raise unauthorized(exc.message) from exc


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, request: Request, db: DbSession) -> TokenResponse:
    service = AuthService(db)
    try:
        return await service.login(
            data,
            user_agent=request.headers.get("user-agent"),
            ip=request.client.host if request.client else None,
        )
    except JAIOSException as exc:
        raise unauthorized(exc.message) from exc


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: DbSession) -> TokenResponse:
    service = AuthService(db)
    try:
        return await service.refresh(data.refresh_token)
    except JAIOSException as exc:
        raise unauthorized(exc.message) from exc
