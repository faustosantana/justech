"""Schemas API — usuarios del tenant."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class TenantUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class TenantUserListResponse(BaseModel):
    items: list[TenantUserResponse]
    total: int
