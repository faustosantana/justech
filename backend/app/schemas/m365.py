"""Schemas API — Microsoft 365 Intelligence Center."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

NOT_CONNECTED_MESSAGE = "Microsoft 365 no conectado"


class M365ConfigKey(BaseModel):
    key: str
    label: str
    description: str
    configured: bool = False


class M365RequiredConfig(BaseModel):
    read_only: bool = True
    redirect_uri: str
    missing_env_keys: list[str] = Field(default_factory=list)
    config_keys: list[M365ConfigKey] = Field(default_factory=list)
    delegated_scopes: list[str] = Field(default_factory=list)
    application_scopes: list[str] = Field(default_factory=list)
    oauth_ready: bool = False
    graph_ready: bool = False
    multi_user_ready: bool = False
    indexing_ready: bool = False
    enterprise_search_ready: bool = False
    hermes_memory_ready: bool = False
    qdrant_ready: bool = False


class M365SetupStep(BaseModel):
    step: int
    title: str
    description: str
    status: str = "pending"


class M365Diagnostics(BaseModel):
    api_reachable: bool = True
    graph_configured: bool = False
    oauth_implemented: bool = False
    graph_implemented: bool = False
    read_only_enforced: bool = True
    audit_enabled: bool = True
    notes: list[str] = Field(default_factory=list)


class M365HealthResponse(BaseModel):
    connected: bool = False
    read_only: bool = True
    message: str = NOT_CONNECTED_MESSAGE
    required_config: M365RequiredConfig
    diagnostics: M365Diagnostics | None = None


class M365StatusResponse(BaseModel):
    connected: bool = False
    read_only: bool = True
    message: str = NOT_CONNECTED_MESSAGE
    required_config: M365RequiredConfig
    setup_steps: list[M365SetupStep] = Field(default_factory=list)
    diagnostics: M365Diagnostics | None = None


class M365ListResponse(BaseModel):
    items: list[Any] = Field(default_factory=list)
    total: int = 0
    connected: bool = False
    read_only: bool = True
    message: str = NOT_CONNECTED_MESSAGE
    required_config: M365RequiredConfig


class M365SearchResponse(BaseModel):
    query: str = ""
    hits: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    connected: bool = False
    read_only: bool = True
    message: str = NOT_CONNECTED_MESSAGE
    required_config: M365RequiredConfig
