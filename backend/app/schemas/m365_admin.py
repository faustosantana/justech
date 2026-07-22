"""Schemas — administración Microsoft 365."""

from __future__ import annotations

from pydantic import BaseModel, Field


class M365AdminConfigResponse(BaseModel):
    tenant_id: str
    client_id: str
    client_secret_configured: bool
    client_secret_masked: str
    redirect_uri: str
    webhook_url: str
    webhook_client_state_configured: bool
    read_only: bool
    oauth_ready: bool
    source: str = "env"


class M365AdminConfigUpdateRequest(BaseModel):
    client_secret: str | None = Field(default=None, min_length=8)
    webhook_client_state: str | None = None


class M365GraphPermissionCheck(BaseModel):
    scope: str
    required: bool
    description: str


class M365ConnectionTestResponse(BaseModel):
    ok: bool
    message: str
    token_acquired: bool = False
    graph_reachable: bool = False
    user_display_name: str | None = None


class M365GraphPermissionsResponse(BaseModel):
    delegated_scopes: list[M365GraphPermissionCheck]
    application_scopes: list[M365GraphPermissionCheck]
    admin_consent_required: bool = True


class M365WebhookRenewResponse(BaseModel):
    ok: bool
    message: str
    subscription_id: str | None = None
    expiration: str | None = None
