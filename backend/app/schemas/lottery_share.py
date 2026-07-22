"""Schemas para shares seguros y sync dry-run."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LotteryShareCreateRequest(BaseModel):
    query_type: Literal["by_date", "range", "by_number", "frequencies", "compare", "repetitions", "next_occurrences"]
    query_parameters: dict[str, Any] = Field(default_factory=dict)
    title: str = Field(min_length=1, max_length=255)
    ttl_hours: int = Field(default=24, ge=1, le=168)
    max_views: int | None = Field(default=50, ge=1, le=10_000)
    allow_export: bool = False


class LotteryShareResponse(BaseModel):
    share_id: UUID
    title: str
    query_type: str
    expires_at: datetime
    revoked_at: datetime | None = None
    max_views: int | None = None
    view_count: int = 0
    allow_export: bool = False
    status: str
    share_url: str | None = None
    # token solo se devuelve una vez al crear
    token: str | None = None
    created_at: datetime | None = None


class LotteryShareListResponse(BaseModel):
    items: list[LotteryShareResponse]
    total: int


class LotterySharedViewResponse(BaseModel):
    title: str
    query_type: str
    generated_at: datetime | None = None
    expires_at: datetime
    disclaimer: str
    branding: str = "JAIOS · Resultados de Loterías"
    result: dict[str, Any]
    allow_export: bool = False


class LotterySyncDryRunRequest(BaseModel):
    from_date: str | None = None
    to_date: str | None = None
    lottery_source_id: int | None = None
    source: Literal["sqlite", "api"] = "sqlite"
    limit: int = Field(default=500, ge=1, le=5000)


class LotterySyncDryRunResponse(BaseModel):
    run_id: UUID | None = None
    dry_run: bool = True
    status: str
    source: str
    records_fetched: int = 0
    records_new: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    conflicts: int = 0
    errors: int = 0
    classifications: dict[str, int] = Field(default_factory=dict)
    sample: list[dict[str, Any]] = Field(default_factory=list)
    wrote_to_database: bool = False
    report_path: str | None = None
