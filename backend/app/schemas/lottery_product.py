"""Schemas producto Fase 5 — dashboard, favoritos, prefs, exports."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.lottery import DrawResult, LotteryLotteryResponse


class LotteryDashboardResponse(BaseModel):
    module_enabled: bool
    sync_enabled: bool
    lotteries_count: int
    draws_count: int
    numbers_count: int
    first_draw_date: str | None = None
    last_draw_date: str | None = None
    favorites: list[LotteryLotteryResponse] = Field(default_factory=list)
    recent_queries: list["LotteryRecentQueryResponse"] = Field(default_factory=list)
    saved_queries: list[dict[str, Any]] = Field(default_factory=list)
    note: str | None = None
    disclaimer: str = (
        "Los resultados históricos y las estadísticas son únicamente informativos. "
        "No garantizan resultados futuros."
    )


class LotteryDetailResponse(BaseModel):
    lottery: LotteryLotteryResponse
    aliases: list[str] = Field(default_factory=list)
    is_favorite: bool = False
    recent_draws: list[DrawResult] = Field(default_factory=list)


class LotteryFavoriteResponse(BaseModel):
    lottery_id: UUID
    lottery: LotteryLotteryResponse
    display_order: int = 0
    created_at: datetime | None = None


class LotteryFavoriteListResponse(BaseModel):
    items: list[LotteryFavoriteResponse]
    total: int


class LotteryFavoriteReorderRequest(BaseModel):
    lottery_ids: list[UUID] = Field(min_length=1, max_length=50)


class LotteryPreferences(BaseModel):
    default_lottery_id: UUID | None = None
    default_date_mode: Literal["exact", "range"] = "exact"
    default_range_days: int = Field(default=7, ge=1, le=3660)
    default_page_size: int = Field(default=50, ge=10, le=500)
    preferred_export_format: Literal["csv", "xlsx", "pdf"] = "csv"
    show_source_ids: bool = False
    compact_results: bool = False
    timezone: str = "America/Santo_Domingo"
    date_format: str = "YYYY-MM-DD"
    first_day_of_week: int = Field(default=1, ge=0, le=6)
    disclaimer_acknowledged: bool = False
    onboarding_completed: bool = False


class LotteryPreferencesUpdate(BaseModel):
    default_lottery_id: UUID | None = None
    default_date_mode: Literal["exact", "range"] | None = None
    default_range_days: int | None = Field(default=None, ge=1, le=3660)
    default_page_size: int | None = Field(default=None, ge=10, le=500)
    preferred_export_format: Literal["csv", "xlsx", "pdf"] | None = None
    show_source_ids: bool | None = None
    compact_results: bool | None = None
    timezone: str | None = None
    date_format: str | None = None
    first_day_of_week: int | None = Field(default=None, ge=0, le=6)
    disclaimer_acknowledged: bool | None = None
    onboarding_completed: bool | None = None


class LotteryRecentQueryResponse(BaseModel):
    id: UUID
    query_type: str
    title: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class LotteryRecentQueryListResponse(BaseModel):
    items: list[LotteryRecentQueryResponse]
    total: int


class LotteryExportRequest(BaseModel):
    query_type: Literal[
        "by_date",
        "range",
        "by_number",
        "frequencies",
        "repetitions",
        "next_occurrences",
        "compare",
        "cross_lottery",
        "saved_query",
    ]
    query_parameters: dict[str, Any] = Field(default_factory=dict)
    format: Literal["csv", "xlsx", "pdf"]
    title: str | None = None
    include_summary: bool = True
    include_metadata: bool = True
    include_disclaimer: bool = True
    timezone: str = "America/Santo_Domingo"
    locale: str = "es"


class LotteryExportResponse(BaseModel):
    export_id: UUID
    status: str
    filename: str
    mime_type: str
    size: int
    row_count: int | None = None
    expires_at: datetime
    download_url: str


class OnboardingState(BaseModel):
    completed: bool = False
    skipped: bool = False
    step: int = 0
