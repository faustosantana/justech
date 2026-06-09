"""Esquemas internos Microsoft 365 — preparación Graph / OAuth."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class M365OAuthTokens(BaseModel):
    """Tokens OAuth — persistencia futura por usuario/tenant."""

    access_token: str
    refresh_token: str | None = None
    expires_at: datetime | None = None
    scopes: list[str] = Field(default_factory=list)
    user_id: str | None = None
    tenant_id: str | None = None


class M365GraphUser(BaseModel):
    id: str | None = None
    display_name: str | None = None
    mail: str | None = None
    user_principal_name: str | None = None


class M365OutlookMessage(BaseModel):
    id: str | None = None
    subject: str = ""
    sender: str = ""
    received_at: datetime | None = None
    preview: str = ""
    web_link: str | None = None
    has_attachments: bool = False


class M365SharePointSite(BaseModel):
    id: str | None = None
    name: str = ""
    web_url: str | None = None
    description: str | None = None


class M365DriveItem(BaseModel):
    id: str | None = None
    name: str = ""
    path: str = ""
    web_url: str | None = None
    modified_at: datetime | None = None
    mime_type: str | None = None
    size_bytes: int | None = None


class M365CalendarEvent(BaseModel):
    id: str | None = None
    subject: str = ""
    start: datetime | None = None
    end: datetime | None = None
    location: str | None = None
    organizer: str | None = None
    web_link: str | None = None


class M365Team(BaseModel):
    id: str | None = None
    display_name: str = ""
    description: str | None = None
    web_url: str | None = None


class M365DocumentItem(BaseModel):
    id: str | None = None
    title: str = ""
    source: str = ""
    web_url: str | None = None
    modified_at: datetime | None = None
    snippet: str | None = None


class M365SearchHit(BaseModel):
    resource_type: str
    title: str
    snippet: str | None = None
    web_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class M365RateLimitState(BaseModel):
    """Estado de rate limiting — Redis futuro."""

    remaining: int | None = None
    reset_at: datetime | None = None
    throttled: bool = False
