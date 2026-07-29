"""Investigation Workspace Asset — operable result tables (MVP)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ASSET_TTL_SECONDS = 600

AssetType = Literal["result_table", "summary", "comparison", "timeline", "export_file"]
WorkspaceAction = Literal[
    "show_results",
    "filter_results",
    "sort_results",
    "export_results",
    "paginate_results",
    "open_asset",
    "summarize_asset",
]

SAME_DAY_COLUMNS: list[str] = [
    "fecha",
    "loteria",
    "numero_a",
    "posicion_a",
    "numero_b",
    "posicion_b",
    "tipo_coincidencia",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AssetFilters(BaseModel):
    model_config = {"extra": "ignore"}

    lottery: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    position: int | None = None
    number: str | None = None
    same_lottery: bool | None = None
    same_position: bool | None = None
    limit: int | None = None


class AssetSort(BaseModel):
    model_config = {"extra": "ignore"}

    field: str = "fecha"
    direction: Literal["asc", "desc"] = "desc"


class AssetPagination(BaseModel):
    model_config = {"extra": "ignore"}

    page: int = 1
    page_size: int = 20


class InvestigationAsset(BaseModel):
    """Structured operable asset for an investigation."""

    model_config = {"extra": "ignore"}

    asset_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    investigation_id: str | None = None
    conversation_id: str | None = None
    asset_type: AssetType = "result_table"
    title: str = ""
    subjects: list[str] = Field(default_factory=list)
    relation: str | None = None
    scope: str = "official_seven"
    columns: list[str] = Field(default_factory=lambda: list(SAME_DAY_COLUMNS))
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    filters: AssetFilters = Field(default_factory=AssetFilters)
    sort: AssetSort = Field(default_factory=AssetSort)
    pagination: AssetPagination = Field(default_factory=AssetPagination)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime = Field(
        default_factory=lambda: _utcnow() + timedelta(seconds=ASSET_TTL_SECONDS)
    )
    source_query_hash: str | None = None
    evidence_hash: str | None = None
    # Full unfiltered/unsorted source rows (for re-apply ops)
    source_rows: list[dict[str, Any]] = Field(default_factory=list)
    export_path: str | None = None
    export_filename: str | None = None
    download_url: str | None = None

    def touch(self) -> "InvestigationAsset":
        now = _utcnow()
        self.updated_at = now
        self.expires_at = now + timedelta(seconds=ASSET_TTL_SECONDS)
        return self

    def is_expired(self, *, now: datetime | None = None) -> bool:
        ts = now or _utcnow()
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return ts >= exp

    def to_store(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_store(cls, data: dict[str, Any] | None) -> "InvestigationAsset | None":
        if not data or not isinstance(data, dict):
            return None
        try:
            return cls.model_validate(data)
        except Exception:  # noqa: BLE001
            return None

    def view_page(self) -> list[dict[str, Any]]:
        start = max(0, (self.pagination.page - 1) * self.pagination.page_size)
        end = start + self.pagination.page_size
        return list(self.rows[start:end])

    def ui_payload(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "title": self.title,
            "subjects": self.subjects,
            "relation": self.relation,
            "scope": self.scope,
            "columns": self.columns,
            "rows": self.view_page(),
            "row_count": self.row_count,
            "total_source": len(self.source_rows),
            "filters": self.filters.model_dump(exclude_none=True),
            "sort": self.sort.model_dump(),
            "pagination": {
                **self.pagination.model_dump(),
                "total_pages": max(
                    1,
                    (self.row_count + self.pagination.page_size - 1)
                    // max(1, self.pagination.page_size),
                ),
            },
            "download_url": self.download_url,
            "export_filename": self.export_filename,
            "controls": [
                "Ver tabla",
                "Filtrar",
                "Ordenar",
                "Exportar Excel",
                "Ver resumen",
            ],
        }


class WorkspaceActionDecision(BaseModel):
    turn_type: Literal["asset_action"] = "asset_action"
    action: WorkspaceAction
    asset_id: str | None = None
    filters: AssetFilters = Field(default_factory=AssetFilters)
    sort: AssetSort | None = None
    pagination: AssetPagination | None = None
    export_format: Literal["xlsx"] | None = None
    requires_sql: bool = False
    requires_asset_load: bool = True
    requires_huawei: bool = False
    confidence: str = "high"
    reason_code: str = "workspace_speech_act"

    def to_trace(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
