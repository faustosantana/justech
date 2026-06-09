import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    create_refresh_token_value,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.tenant import Tenant, TenantMembership
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, data: UserCreate) -> User:
        existing = await self.db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none():
            raise AuthenticationError("Email already registered")

        user = User(
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def login(self, data: LoginRequest, *, user_agent: str | None = None, ip: str | None = None) -> TokenResponse:
        result = await self.db.execute(
            select(User)
            .where(User.email == data.email.lower(), User.is_active.is_(True))
            .options(selectinload(User.memberships).selectinload(TenantMembership.tenant))
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(data.password, user.password_hash):
            raise AuthenticationError("Invalid credentials")

        membership = await self._resolve_membership(user, data.tenant_slug)
        tenant_id = membership.tenant_id if membership else None
        role = membership.role if membership else None

        user.last_login_at = datetime.now(UTC)
        access = create_access_token(
            subject=str(user.id),
            tenant_id=tenant_id,
            role=role,
        )

        refresh_value = create_refresh_token_value()
        refresh = RefreshToken(
            user_id=user.id,
            tenant_id=tenant_id,
            token_hash=hash_token(refresh_value),
            expires_at=datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days),
            user_agent=user_agent,
            ip_address=ip,
        )
        self.db.add(refresh)

        return TokenResponse(
            access_token=access,
            refresh_token=refresh_value,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            tenant_id=tenant_id,
            role=role,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        stored = result.scalar_one_or_none()
        if not stored or stored.expires_at < datetime.now(UTC):
            raise AuthenticationError("Invalid or expired refresh token")

        role: str | None = None
        if stored.tenant_id:
            mem = await self.db.execute(
                select(TenantMembership).where(
                    TenantMembership.user_id == stored.user_id,
                    TenantMembership.tenant_id == stored.tenant_id,
                )
            )
            membership = mem.scalar_one_or_none()
            role = membership.role if membership else None

        access = create_access_token(
            subject=str(stored.user_id),
            tenant_id=stored.tenant_id,
            role=role,
        )
        return TokenResponse(
            access_token=access,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            tenant_id=stored.tenant_id,
            role=role,
        )

    async def _resolve_membership(
        self, user: User, tenant_slug: str | None
    ) -> TenantMembership | None:
        if not user.memberships:
            return None

        if tenant_slug:
            for m in user.memberships:
                if m.tenant.slug == tenant_slug:
                    return m
            raise AuthenticationError(f"No access to tenant '{tenant_slug}'")

        for m in user.memberships:
            if m.is_default:
                return m
        return user.memberships[0]
