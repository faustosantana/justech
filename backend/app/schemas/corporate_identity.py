"""Schemas — identidad corporativa."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CorporateIdentityAssetResponse(BaseModel):
    id: uuid.UUID | None = None
    asset_type: str
    company_key: str | None = None
    company_label: str | None = None
    filename: str
    status: str
    storage_relative_path: str | None = None
    uploaded_at: datetime | None = None
    uploaded_by: uuid.UUID | None = None
    preview_url: str | None = None
    warnings: list[str] = Field(default_factory=list)


class CorporateIdentityOverviewResponse(BaseModel):
    root_path: str
    metadata_loaded: bool
    default_signature: str
    active_company_key: str | None = None
    active_company_label: str | None = None
    signature: CorporateIdentityAssetResponse | None = None
    stamp: CorporateIdentityAssetResponse | None = None
    signatures: list[CorporateIdentityAssetResponse] = Field(default_factory=list)
    stamps: list[CorporateIdentityAssetResponse] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)
    placement: dict[str, Any] = Field(default_factory=dict)


class CorporateIdentityUploadResponse(BaseModel):
    asset: CorporateIdentityAssetResponse
    message: str
