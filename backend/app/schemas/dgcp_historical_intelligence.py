"""Schemas — Inteligencia histórica 360° DGCP (adjudicaciones verificables)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


DataQuality = Literal["VERIFICADO", "PARCIAL", "INCOMPLETO"]
MatchClass = Literal["EXACTA", "ALTA_SIMILITUD", "RELACIONADA"]
ConcentrationLevel = Literal["BAJA", "MEDIA", "ALTA", "INSUFICIENTE"]


class HistoricalSourceRef(BaseModel):
    source: str = "dgcp_contratos"
    source_url: str | None = None
    process_url: str | None = None
    contract_url: str | None = None
    dgcp_process_code: str | None = None
    retrieved_at: str | None = None
    document_reference: str | None = None


class HistoricalPurchaseRow(BaseModel):
    award_id: str
    process_code: str
    contract_code: str | None = None
    award_date: str | None = None
    institution: str
    description: str | None = None
    supplier_name: str | None = None
    supplier_rpe: str | None = None
    supplier_rnc: str | None = None
    awarded_amount: Decimal | None = None
    estimated_amount: Decimal | None = None
    currency: str = "DOP"
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    unit_measure: str | None = None
    modality: str | None = None
    award_status: str | None = None
    match_class: MatchClass = "RELACIONADA"
    match_class_label: str = "Compra relacionada"
    similarity_score: float = 0
    similarity_pct: float | None = None
    match_reasons: list[str] = Field(default_factory=list)
    data_quality: DataQuality = "PARCIAL"
    source: HistoricalSourceRef = Field(default_factory=HistoricalSourceRef)


class LastPurchaseBlock(BaseModel):
    available: bool = False
    title: str = "Sin compra comparable verificable"
    match_class: MatchClass | None = None
    match_class_label: str | None = None
    criterion: str | None = None
    purchase: HistoricalPurchaseRow | None = None
    caveats: list[str] = Field(default_factory=list)


class LastSupplierBlock(BaseModel):
    available: bool = False
    supplier_name: str | None = None
    supplier_rpe: str | None = None
    award_date: str | None = None
    awarded_amount: Decimal | None = None
    currency: str = "DOP"
    process_code: str | None = None
    source_url: str | None = None


class SupplierRankRow(BaseModel):
    supplier_name: str
    supplier_rpe: str | None = None
    awards_count: int
    processes_count: int
    total_amount: Decimal
    currency: str = "DOP"
    last_award_date: str | None = None
    share_pct: float


class ConcentrationBlock(BaseModel):
    level: ConcentrationLevel = "INSUFICIENTE"
    top1_share_pct: float | None = None
    top3_share_pct: float | None = None
    suppliers_count: int = 0
    note: str = "Indicador comercial descriptivo; no implica irregularidad."


class PricePoint(BaseModel):
    award_date: str | None = None
    supplier_name: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    awarded_amount: Decimal | None = None
    process_code: str | None = None
    source_url: str | None = None


class PriceHistoryBlock(BaseModel):
    available: bool = False
    currency: str = "DOP"
    points: list[PricePoint] = Field(default_factory=list)
    last_unit_price: Decimal | None = None
    avg_unit_price: Decimal | None = None
    min_unit_price: Decimal | None = None
    max_unit_price: Decimal | None = None
    median_unit_price: Decimal | None = None
    variation_vs_last_pct: float | None = None
    caveats: list[str] = Field(default_factory=list)


class FrequencyBlock(BaseModel):
    available: bool = False
    first_purchase_date: str | None = None
    last_purchase_date: str | None = None
    process_count: int = 0
    purchase_count: int = 0
    months_span: int | None = None
    approx_months_between: float | None = None
    summary: str = ""
    temporal_pattern: str | None = None


class ModalityStatsRow(BaseModel):
    modality: str
    process_count: int
    total_amount: Decimal
    suppliers_count: int


class ProductLineHistory(BaseModel):
    line_number: int | None = None
    requested_description: str
    last_purchase: HistoricalPurchaseRow | None = None
    match_class: MatchClass | None = None
    similarity_pct: float | None = None


class BudgetComparisonBlock(BaseModel):
    available: bool = False
    current_estimated_amount: Decimal | None = None
    current_currency: str = "DOP"
    last_comparable_amount: Decimal | None = None
    variation_pct: float | None = None
    caveats: list[str] = Field(default_factory=list)


class InstitutionProfileBlock(BaseModel):
    institution: str
    known_award_lines: int = 0
    known_processes: int = 0
    known_suppliers: int = 0
    total_awarded_amount: Decimal | None = None
    currency: str = "DOP"
    modalities: list[ModalityStatsRow] = Field(default_factory=list)


class SupplierProfileBlock(BaseModel):
    supplier_name: str
    supplier_rpe: str | None = None
    awards_count: int = 0
    total_awarded: Decimal | None = None
    currency: str = "DOP"
    institutions_won: list[str] = Field(default_factory=list)
    last_award_date: str | None = None
    recent_processes: list[str] = Field(default_factory=list)
    top_categories: list[str] = Field(default_factory=list)


class ExecutiveSummaryBlock(BaseModel):
    paragraphs: list[str] = Field(default_factory=list)
    based_on_metrics_only: bool = True


class DataQualitySummary(BaseModel):
    overall: DataQuality = "INCOMPLETO"
    verified_count: int = 0
    partial_count: int = 0
    incomplete_count: int = 0
    notes: list[str] = Field(default_factory=list)


class CurrentProcessBrief(BaseModel):
    opportunity_id: UUID
    process_code: str
    title: str | None = None
    institution: str
    estimated_amount: Decimal | None = None
    currency: str = "DOP"
    modality: str | None = None
    objeto_proceso: str | None = None
    status: str | None = None
    amount_kind: Literal["estimado"] = "estimado"


class DGCPHistoricalIntelligenceResponse(BaseModel):
    current_process: CurrentProcessBrief
    window_months: int | None = None
    last_purchase: LastPurchaseBlock = Field(default_factory=LastPurchaseBlock)
    last_supplier: LastSupplierBlock = Field(default_factory=LastSupplierBlock)
    institution_purchases: list[HistoricalPurchaseRow] = Field(default_factory=list)
    suppliers_ranking: list[SupplierRankRow] = Field(default_factory=list)
    concentration: ConcentrationBlock = Field(default_factory=ConcentrationBlock)
    product_lines: list[ProductLineHistory] = Field(default_factory=list)
    price_history: PriceHistoryBlock = Field(default_factory=PriceHistoryBlock)
    frequency: FrequencyBlock = Field(default_factory=FrequencyBlock)
    modalities: list[ModalityStatsRow] = Field(default_factory=list)
    related_processes: list[HistoricalPurchaseRow] = Field(default_factory=list)
    budget_comparison: BudgetComparisonBlock = Field(default_factory=BudgetComparisonBlock)
    institution_profile: InstitutionProfileBlock | None = None
    executive_summary: ExecutiveSummaryBlock = Field(default_factory=ExecutiveSummaryBlock)
    data_quality: DataQualitySummary = Field(default_factory=DataQualitySummary)
    statistics: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float | None = None
    indexed_lines_scanned: int = 0
    message: str = ""
