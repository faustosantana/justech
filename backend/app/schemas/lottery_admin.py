"""Schemas administrativos Lottery 2.0."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LotteryAdminLotteryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: int
    name: str
    commercial_name: str | None = None
    short_name: str | None = None
    normalized_name: str
    slug: str
    country: str | None = None
    timezone: str
    currency: str | None = None
    active: bool
    is_loto: bool = False
    is_aggregate: bool = False
    is_visible: bool = True
    is_visible_dashboard: bool = True
    is_visible_catalog: bool = True
    is_searchable: bool = True
    is_ai_enabled: bool = True
    is_comparable: bool = True
    is_sync_enabled: bool = False
    is_auto_write_enabled: bool = False
    is_featured: bool = False
    display_order: int = 1000
    logo_url: str | None = None
    icon_key: str | None = None
    data_source: str | None = None
    adapter_key: str | None = None
    external_id: str | None = None
    draw_schedule_cron: str | None = None
    draw_days: str | None = None
    draw_times: str | None = None
    sync_interval_minutes: int | None = None
    sync_post_draw_delay_minutes: int | None = None
    sync_max_retries: int | None = None
    sync_active_hours: str | None = None
    last_sync_at: datetime | None = None
    last_result_at: datetime | None = None
    next_draw_estimated_at: datetime | None = None
    health_status: str = "unknown"
    last_error: str | None = None
    draw_count: int = 0
    numbers_count: int = 0
    first_draw_date: date | None = None
    last_draw_date: date | None = None
    admin_notes: str | None = None


class LotteryAdminLotteryUpdate(BaseModel):
    active: bool | None = None
    is_visible: bool | None = None
    is_visible_dashboard: bool | None = None
    is_visible_catalog: bool | None = None
    is_searchable: bool | None = None
    is_ai_enabled: bool | None = None
    is_comparable: bool | None = None
    is_sync_enabled: bool | None = None
    is_auto_write_enabled: bool | None = None
    is_featured: bool | None = None
    display_order: int | None = Field(default=None, ge=0, le=100000)
    commercial_name: str | None = None
    short_name: str | None = None
    logo_url: str | None = None
    icon_key: str | None = None
    country: str | None = None
    timezone: str | None = None
    currency: str | None = None
    data_source: str | None = None
    adapter_key: str | None = None
    external_id: str | None = None
    draw_schedule_cron: str | None = None
    draw_days: str | None = None
    draw_times: str | None = None
    sync_interval_minutes: int | None = Field(default=None, ge=1, le=10080)
    sync_post_draw_delay_minutes: int | None = Field(default=None, ge=0, le=1440)
    sync_max_retries: int | None = Field(default=None, ge=0, le=20)
    sync_active_hours: str | None = None
    health_status: str | None = None
    admin_notes: str | None = None


BulkAction = Literal[
    "enable",
    "disable",
    "show",
    "hide",
    "allow_search",
    "block_search",
    "enable_ai",
    "disable_ai",
    "enable_sync",
    "disable_sync",
    "enable_auto_write",
    "disable_auto_write",
    "feature",
    "unfeature",
    "set_order",
]


class LotteryAdminBulkRequest(BaseModel):
    lottery_ids: list[UUID] = Field(min_length=1, max_length=200)
    action: BulkAction
    display_order: int | None = Field(default=None, ge=0, le=100000)


class LotteryAdminBulkResponse(BaseModel):
    updated: int
    action: str


class LotteryCatalogCard(BaseModel):
    id: UUID
    slug: str
    name: str
    commercial_name: str | None = None
    short_name: str | None = None
    country: str | None = None
    country_code: str | None = None
    flag_emoji: str | None = None
    timezone: str | None = None
    logo_url: str | None = None
    icon_key: str | None = None
    is_featured: bool = False
    is_favorite: bool = False
    draw_count: int = 0
    last_draw_date: date | None = None
    last_numbers: list[str] = Field(default_factory=list)
    last_sync_at: datetime | None = None
    next_draw_estimated_at: datetime | None = None
    draw_times: str | None = None
    health_status: str = "unknown"
    is_searchable: bool = True
    is_comparable: bool = True
    is_ai_enabled: bool = True
    is_sync_enabled: bool = False


class LotteryCatalogResponse(BaseModel):
    items: list[LotteryCatalogCard]
    total: int
    page: int
    page_size: int


class LotteryDashboardV2(BaseModel):
    lotteries_active: int
    lotteries_visible: int
    lotteries_synced: int
    results_today: int
    draws_historical: int
    numbers_stored: int
    last_update_at: datetime | None = None
    sources_healthy: int
    sources_error: int
    latest_results: list[dict[str, Any]] = Field(default_factory=list)
    featured: list[LotteryCatalogCard] = Field(default_factory=list)
    favorites: list[LotteryCatalogCard] = Field(default_factory=list)
    top_numbers: list[dict[str, Any]] = Field(default_factory=list)
    bottom_numbers: list[dict[str, Any]] = Field(default_factory=list)
    recent_queries: list[dict[str, Any]] = Field(default_factory=list)
    sync_summary: dict[str, Any] = Field(default_factory=dict)
    coverage: dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = (
        "Análisis histórico únicamente. No garantiza resultados futuros ni constituye "
        "recomendación de apuestas."
    )


class LotteryDashboardV3(LotteryDashboardV2):
    """Executive ops dashboard — Lottery 3.0."""

    local_today: date | None = None
    timezone: str = "America/Santo_Domingo"
    pending_results: int = 0
    expected_today: int = 0
    pending_sync_enabled: int = 0
    pending_visible: int = 0
    last_sync_at: datetime | None = None
    next_sync_at: datetime | None = None
    worker_status: dict[str, Any] = Field(default_factory=dict)
    recent_sync_runs: list[dict[str, Any]] = Field(default_factory=list)
    next_sync_windows: list[dict[str, Any]] = Field(default_factory=list)
    circuit_breakers: list[dict[str, Any]] = Field(default_factory=list)
    source_health: list[dict[str, Any]] = Field(default_factory=list)
    kpis: dict[str, Any] = Field(default_factory=dict)
    results_today_note: str = (
        "Resultados hoy = draws con draw_date = hoy local (America/Santo_Domingo). "
        "Pendientes sync = loterías con sync_enabled sin resultado de hoy. "
        "Pendientes visibles = loterías del dashboard sin resultado de hoy (incluye no sincronizadas)."
    )
