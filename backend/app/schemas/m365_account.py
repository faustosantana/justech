"""Schemas — cuentas M365 por usuario."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class M365AccountResponse(BaseModel):
    id: uuid.UUID
    jaios_user_id: uuid.UUID
    jaios_user_name: str | None = None
    jaios_user_email: str | None = None
    email: str | None = None
    microsoft_user_id: str | None = None
    display_name: str | None = None
    connection_status: str
    scopes_granted: list[str] = Field(default_factory=list)
    token_expires_at: datetime | None = None
    last_sync_at: datetime | None = None
    is_active: bool
    can_connect: bool = True
    required_scopes: list[str] = Field(default_factory=list)


class M365AccountListResponse(BaseModel):
    items: list[M365AccountResponse]
    total: int


class M365AccountPrepareRequest(BaseModel):
    email: str | None = None
    jaios_user_id: uuid.UUID | None = None
