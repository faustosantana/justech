"""Schemas Pydantic del módulo lottery (Fase 1–3)."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LotteryHealthResponse(BaseModel):
    module_enabled: bool
    database_connection: bool
    schema_available: bool
    import_status: str
    sync_status: str
    timestamp: datetime
    version: str = "0.3.0-phase3"
    lotteries_count: int = 0
    draws_count: int = 0
    note: str | None = None


class LotteryLotteryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: int
    name: str
    normalized_name: str
    slug: str
    country: str | None = None
    timezone: str
    active: bool
    is_loto: bool = False
    is_aggregate: bool = False
    first_draw_date: date | None = None
    last_draw_date: date | None = None
    draw_count: int = 0
    # Lottery 2.0 flags (optional for backward-compatible clients)
    is_visible: bool = True
    is_searchable: bool = True
    is_ai_enabled: bool = True
    is_comparable: bool = True
    is_sync_enabled: bool = False
    is_featured: bool = False
    commercial_name: str | None = None
    short_name: str | None = None
    display_order: int = 1000
    health_status: str = "unknown"


class LotteryListResponse(BaseModel):
    items: list[LotteryLotteryResponse]
    total: int
    module_enabled: bool = True
    note: str | None = None


class LotteryAliasCandidate(BaseModel):
    source_id: int
    name: str
    confidence: str = Field(description="high|medium|low")
    id: UUID | None = None
    slug: str | None = None


class LotteryAliasResolution(BaseModel):
    query: str
    resolved: bool
    ambiguous: bool = False
    status: str | None = None
    lottery: LotteryLotteryResponse | None = None
    source_id: int | None = None
    candidates: list[LotteryAliasCandidate] = Field(default_factory=list)
    message: str | None = None


class WarningMessage(BaseModel):
    code: str
    message: str


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class DrawNumberResult(BaseModel):
    position: int
    position_label: str
    number_value: str
    number_raw: str
    number_type: str


class DrawResult(BaseModel):
    id: UUID
    draw_date: date
    draw_time: time | None = None
    game_name: str
    source_reference: str | None = None
    numbers: list[DrawNumberResult] = Field(default_factory=list)


class QueryMeta(BaseModel):
    query: dict[str, Any]
    resolved_lottery: LotteryLotteryResponse | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    warnings: list[WarningMessage] = Field(default_factory=list)
    generated_at: datetime


class DateQueryResponse(BaseModel):
    meta: QueryMeta
    date: date
    total: int
    draws: list[DrawResult]


class RangeQueryResponse(BaseModel):
    meta: QueryMeta
    from_date: date
    to_date: date
    pagination: PaginationMeta
    draws: list[DrawResult]


class CalendarWindowResponse(BaseModel):
    meta: QueryMeta
    days_requested: int
    include_base_date: bool
    calendar_from: date
    calendar_to: date
    days_with_draws: list[date]
    days_without_draws: list[date]
    total_draws: int
    draws: list[DrawResult]


class DrawsWindowResponse(BaseModel):
    meta: QueryMeta
    count_requested: int
    include_base_date: bool
    total: int
    draws: list[DrawResult]
    chronological: bool = True


class NumberOccurrence(BaseModel):
    draw_id: UUID
    draw_date: date
    draw_time: time | None
    game_name: str
    position: int
    position_label: str
    number_value: str
    number_type: str


class NumberSearchResponse(BaseModel):
    meta: QueryMeta
    number: str
    pagination: PaginationMeta
    occurrences: list[NumberOccurrence]


class FrequencyItem(BaseModel):
    number: str
    count: int
    percentage: float


class FrequencyResponse(BaseModel):
    meta: QueryMeta
    from_date: date
    to_date: date
    total_observations: int
    items: list[FrequencyItem]


class RepetitionItem(BaseModel):
    number: str
    count: int
    first_date: date
    last_date: date
    dates: list[date]
    positions: list[int] = Field(default_factory=list)


class RepetitionResponse(BaseModel):
    meta: QueryMeta
    from_date: date
    to_date: date
    min_count: int
    items: list[RepetitionItem]


class NextOccurrenceItem(BaseModel):
    draw_id: UUID
    draw_date: date
    draw_time: time | None
    position: int
    position_label: str
    number_value: str
    number_type: str


class NextOccurrencesResponse(BaseModel):
    meta: QueryMeta
    number: str
    after_date: date
    note: str = "Próxima aparición histórica — no es predicción."
    items: list[NextOccurrenceItem]


class CompareRequest(BaseModel):
    lotteries: list[str] = Field(min_length=2, max_length=10)
    from_date: date = Field(alias="from")
    to_date: date = Field(alias="to")
    mode: Literal["same_date", "repeated_numbers", "frequencies", "intersections", "timeline"]
    position: int | None = None
    number_type: str | None = None
    include_draws: bool = False
    limit: int = Field(default=50, ge=1, le=200)
    intersection_scope: Literal["same_day", "within_range"] = "within_range"

    model_config = ConfigDict(populate_by_name=True)


class ComparisonResponse(BaseModel):
    meta: QueryMeta
    mode: str
    lotteries: list[LotteryLotteryResponse]
    from_date: date
    to_date: date
    data: dict[str, Any]


class CrossLotteryResponse(BaseModel):
    meta: QueryMeta
    mode: str
    lotteries: list[LotteryLotteryResponse]
    from_date: date
    to_date: date
    data: dict[str, Any]
