from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = None
    tax_id: str | None = None


class TenantResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    legal_name: str | None
    tax_id: str | None
    status: str
    plan: str
    created_at: datetime

    model_config = {"from_attributes": True}
