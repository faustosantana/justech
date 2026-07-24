"""Schemas — conectores dinámicos."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConnectorSecretField(BaseModel):
    key: str
    label: str
    masked: str | None = None
    configured: bool = False


class ConnectorEndpointCreate(BaseModel):
    name: str
    path: str
    http_method: str = "GET"
    query_params: dict[str, Any] = Field(default_factory=dict)
    body_template: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    response_hint: dict[str, Any] = Field(default_factory=dict)
    transform: dict[str, Any] = Field(default_factory=dict)
    assistant_enabled: bool = False
    sort_order: int = 0


class ConnectorEndpointResponse(ConnectorEndpointCreate):
    id: UUID
    provider_id: UUID
    created_at: datetime
    updated_at: datetime


class ConnectorCreateRequest(BaseModel):
    name: str
    connector_type: str = "rest_api"
    auth_method: str = "api_key"
    base_url: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, str] = Field(default_factory=dict)
    user_link_mode: str = "none"
    documentation: str | None = None
    read_only: bool = True
    environment: str = "development"
    endpoints: list[ConnectorEndpointCreate] = Field(default_factory=list)


class ConnectorUpdateRequest(BaseModel):
    name: str | None = None
    connector_type: str | None = None
    auth_method: str | None = None
    base_url: str | None = None
    config: dict[str, Any] | None = None
    secrets: dict[str, str] = Field(default_factory=dict)
    delete_secrets: list[str] = Field(default_factory=list)
    user_link_mode: str | None = None
    documentation: str | None = None
    read_only: bool | None = None
    environment: str | None = None
    is_active: bool | None = None


class ConnectorSummary(BaseModel):
    id: str
    slug: str
    name: str
    connector_type: str
    auth_method: str
    base_url: str | None = None
    is_active: bool = True
    is_builtin: bool = False
    is_dynamic: bool = True
    connected: bool = False
    status: str = "not_configured"
    read_only: bool | None = None
    environment: str = "development"
    user_link_mode: str = "none"
    last_test_at: datetime | None = None
    last_test_ok: bool | None = None
    last_test_message: str | None = None
    endpoint_count: int = 0
    user_link_count: int = 0
    config_url: str | None = None
    documentation: str | None = None
    model: str | None = None
    latency_ms: int | None = None


class ConnectorDetailResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    connector_type: str
    auth_method: str
    base_url: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    secrets_masked: dict[str, str | None] = Field(default_factory=dict)
    is_active: bool = True
    is_builtin: bool = False
    user_link_mode: str = "none"
    documentation: str | None = None
    read_only: bool = True
    environment: str = "development"
    connected: bool = False
    status: str = "not_configured"
    last_test_at: datetime | None = None
    last_test_ok: bool | None = None
    last_test_message: str | None = None
    endpoints: list[ConnectorEndpointResponse] = Field(default_factory=list)
    recent_test_logs: list[dict[str, Any]] = Field(default_factory=list)


class ConnectorListResponse(BaseModel):
    environment: str
    builtin_items: list[ConnectorSummary] = Field(default_factory=list)
    dynamic_items: list[ConnectorSummary] = Field(default_factory=list)
    items: list[ConnectorSummary] = Field(default_factory=list)


class ConnectorTestResponse(BaseModel):
    ok: bool
    success: bool = False
    message: str
    error: str | None = None
    missing_config: list[str] = Field(default_factory=list)
    latency_ms: int | None = None
    http_status: int | None = None
    response_preview: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class UserLinkResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_email: str | None = None
    user_name: str | None = None
    external_account_id: str | None = None
    external_account_label: str | None = None
    status: str
    is_active: bool
    last_used_at: datetime | None = None
    linked_at: datetime


class UserLinkCreateRequest(BaseModel):
    external_account_id: str | None = None
    external_account_label: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntegrationRegistryResponse(BaseModel):
    environment: str
    items: list[ConnectorSummary]
