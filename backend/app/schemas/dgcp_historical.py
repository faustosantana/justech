"""Schemas — histórico de adjudicaciones DGCP."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DGCPHistoricalSearchFilters(BaseModel):
    same_institution_only: bool = True
    same_product_only: bool = False
    years_back: int | None = 3
    supplier_name: str | None = None
    min_similarity: float | None = 12
    limit: int = 25


class DGCPHistoricalAwardItem(BaseModel):
    id: str
    process_code: str
    contract_code: str | None = None
    buyer_institution: str
    supplier_name: str | None = None
    award_date: str | None = None
    item_description: str | None = None
    contract_object: str | None = None
    unit_measure: str | None = None
    unit_price: Decimal | None = None
    quantity: Decimal | None = None
    awarded_amount: Decimal | None = None
    modality: str | None = None
    contract_url: str | None = None
    process_url: str | None = None
    source: str = "dgcp_contratos_articulos"
    publication_to_award_days: int | None = None
    similarity_score: float = 0
    similarity_level: str = "—"
    match_reasons: list[str] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)


class DGCPHistoricalIndexMeta(BaseModel):
    total_indexed: int = 0
    institution_indexed: int = 0
    last_indexed_at: str | None = None
    last_index_job_status: str | None = None
    reindex_instructions: str = (
        "Use «Reindexar histórico» para volver a consultar adjudicaciones DGCP de esta institución."
    )
    source: str = "dgcp_api:contratos,contratos/articulos"


class DGCPHistoricalIndicators(BaseModel):
    similar_process_count: int = 0
    similar_item_count: int = 0
    min_unit_price: Decimal | None = None
    avg_unit_price: Decimal | None = None
    max_unit_price: Decimal | None = None
    last_awarded_unit_price: Decimal | None = None
    most_frequent_supplier: str | None = None
    most_frequent_supplier_wins: int = 0
    competition_level: str = "—"


class DGCPHistoricalPriceRecommendation(BaseModel):
    currency: str = "DOP"
    historical_min_unit: Decimal | None = None
    historical_avg_unit: Decimal | None = None
    historical_max_unit: Decimal | None = None
    recommended_offer_low: Decimal | None = None
    recommended_offer_high: Decimal | None = None
    market_supplier_avg: Decimal | None = None
    margin_risk: str | None = None
    summary: str = ""


class DGCPHistoricalAwardsResponse(BaseModel):
    process_code: str | None = None
    process_title: str | None = None
    process_url: str | None = None
    data_available: bool = True
    message: str = ""
    missing_sources: list[str] = Field(default_factory=list)
    matches: list[DGCPHistoricalAwardItem] = Field(default_factory=list)
    indicators: DGCPHistoricalIndicators = Field(default_factory=DGCPHistoricalIndicators)
    price_recommendation: DGCPHistoricalPriceRecommendation | None = None
    ai_insights: list[str] = Field(default_factory=list)
    filters_applied: dict[str, Any] = Field(default_factory=dict)
    total_candidates_scanned: int = 0


class DGCPHistoricalIndexRequest(BaseModel):
    max_pages: int = Field(default=10, ge=1, le=500)
    page_size: int = Field(default=100, ge=10, le=200)


class DGCPHistoricalIndexResponse(BaseModel):
    job_id: UUID
    status: str
    pages_indexed: int
    contracts_indexed: int
    items_indexed: int
    error_message: str | None = None
    message: str = ""


class DGCPHistoricalIndexStatsResponse(BaseModel):
    total_indexed: int
    institution_indexed: int = 0
    institution_name: str | None = None
    institution_code: str | None = None
    last_indexed_at: str | None = None
    last_index_job_status: str | None = None
    data_available: bool = False
    source: str = "dgcp_api:contratos,contratos/articulos"
    reindex_instructions: str = (
        "Use POST /api/v1/dgcp/historical-awards/index o el botón «Reindexar histórico»."
    )


class DGCPHistoricalSearchRequest(BaseModel):
    query: str | None = None
    filters: DGCPHistoricalSearchFilters = Field(default_factory=DGCPHistoricalSearchFilters)


class DGCPHistoricalSimilarSearchRequest(BaseModel):
    refresh: bool = False
    limit: int = Field(default=10, ge=1, le=25)
    extra_query: str | None = None
    max_pages: int | None = Field(default=None, ge=1, le=25)


class DGCPHistoricalSimilarResponse(BaseModel):
    opportunity_id: str
    process_code: str
    process_title: str | None = None
    buyer_institution: str
    keywords_used: list[str] = Field(default_factory=list)
    cached: bool = False
    searched_at: str | None = None
    expires_at: str | None = None
    source: str = "dgcp_api_on_demand"
    pages_scanned: int = 0
    candidates_scanned: int = 0
    status: str = "pending"
    message: str = ""
    error_message: str | None = None
    matches: list[DGCPHistoricalAwardItem] = Field(default_factory=list)
    other_institution_matches: list[DGCPHistoricalAwardItem] = Field(default_factory=list)
    total_matches: int = 0
    indicators: DGCPHistoricalIndicators = Field(default_factory=DGCPHistoricalIndicators)
    price_recommendation: DGCPHistoricalPriceRecommendation | None = None
    ai_insights: list[str] = Field(default_factory=list)
    index_meta: DGCPHistoricalIndexMeta = Field(default_factory=DGCPHistoricalIndexMeta)
    remote_status: str | None = None
    degraded: bool = False
    last_updated_at: str | None = None
    local_latency_ms: float | None = None
    remote_latency_ms: float | None = None
