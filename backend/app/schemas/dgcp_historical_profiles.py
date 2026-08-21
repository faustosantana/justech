"""Schemas — perfiles 360° proveedor / institución (histórico DGCP)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.dgcp_historical_intelligence import (
    ConcentrationBlock,
    DataQualitySummary,
    FrequencyBlock,
    HistoricalPurchaseRow,
    HistoricalSourceRef,
    ModalityStatsRow,
    PriceHistoryBlock,
)

DataQuality = Literal["VERIFICADO", "PARCIAL", "INCOMPLETO"]
Diversification = Literal["DIVERSIFICADO", "MODERADO", "CONCENTRADO", "INSUFICIENTE"]


class ProfileIdentity(BaseModel):
    stable_key: str
    display_name: str
    identity_kind: str  # rnc|rpe|code|name
    identity_confidence: str  # alta|sugerida|baja
    rnc: str | None = None
    rpe: str | None = None
    institution_code: str | None = None
    rnc_available: bool = False
    rpe_available: bool = False
    note: str | None = None


class CurrencyAmount(BaseModel):
    currency: str
    amount: Decimal
    awards_count: int = 0


class TimelineBucket(BaseModel):
    period: str  # YYYY-MM or YYYY
    awards_count: int
    amount: Decimal
    currency: str = "DOP"


class CategoryStatRow(BaseModel):
    category: str
    awards_count: int
    process_count: int
    total_amount: Decimal
    currency: str = "DOP"
    last_award_date: str | None = None


class PartyShareRow(BaseModel):
    name: str
    stable_key: str
    rpe: str | None = None
    rnc: str | None = None
    awards_count: int
    process_count: int
    total_amount: Decimal
    currency: str = "DOP"
    last_award_date: str | None = None
    share_pct: float


class ProductAwardRow(BaseModel):
    description_original: str
    quantity: Decimal | None = None
    unit_measure: str | None = None
    unit_price: Decimal | None = None
    awarded_amount: Decimal | None = None
    currency: str = "DOP"
    institution: str | None = None
    institution_key: str | None = None
    supplier_name: str | None = None
    supplier_key: str | None = None
    award_date: str | None = None
    process_code: str
    source: HistoricalSourceRef = Field(default_factory=HistoricalSourceRef)


class SupplierInstitutionPair(BaseModel):
    supplier_key: str
    supplier_name: str
    institution_key: str
    institution_name: str
    awards_count: int
    process_count: int
    total_amount: Decimal
    currency: str = "DOP"
    first_award_date: str | None = None
    last_award_date: str | None = None
    categories: list[str] = Field(default_factory=list)
    recent_processes: list[str] = Field(default_factory=list)


class DiversificationBlock(BaseModel):
    level: Diversification = "INSUFICIENTE"
    top1_share_pct: float | None = None
    top3_share_pct: float | None = None
    note: str = "Indicador descriptivo de distribución histórica; no implica irregularidad."


class DGCPSupplierProfileResponse(BaseModel):
    identity: ProfileIdentity
    window_months: int | None = None
    data_quality: DataQualitySummary = Field(default_factory=DataQualitySummary)
    totals_by_currency: list[CurrencyAmount] = Field(default_factory=list)
    awards_count: int = 0
    process_count: int = 0
    institutions_count: int = 0
    categories_count: int = 0
    last_award_date: str | None = None
    last_award: HistoricalPurchaseRow | None = None
    last_12m_amount: Decimal | None = None
    last_12m_awards: int = 0
    last_12m_currency: str = "DOP"
    primary_category: str | None = None
    period_from: str | None = None
    period_to: str | None = None
    indexed_at: str | None = None
    executive_summary: list[str] = Field(default_factory=list)
    awards: list[HistoricalPurchaseRow] = Field(default_factory=list)
    institutions: list[PartyShareRow] = Field(default_factory=list)
    categories: list[CategoryStatRow] = Field(default_factory=list)
    products: list[ProductAwardRow] = Field(default_factory=list)
    timeline: list[TimelineBucket] = Field(default_factory=list)
    diversification: DiversificationBlock = Field(default_factory=DiversificationBlock)
    pair: SupplierInstitutionPair | None = None
    modalities: list[ModalityStatsRow] = Field(default_factory=list)
    latency_ms: float | None = None
    rows_scanned: int = 0
    cache_hit: bool = False
    message: str = ""


class DGCPInstitutionProfileResponse(BaseModel):
    identity: ProfileIdentity
    window_months: int | None = None
    data_quality: DataQualitySummary = Field(default_factory=DataQualitySummary)
    totals_by_currency: list[CurrencyAmount] = Field(default_factory=list)
    awards_count: int = 0
    process_count: int = 0
    suppliers_count: int = 0
    categories_count: int = 0
    last_award_date: str | None = None
    last_purchase: HistoricalPurchaseRow | None = None
    last_supplier_name: str | None = None
    last_supplier_key: str | None = None
    primary_category: str | None = None
    period_from: str | None = None
    period_to: str | None = None
    indexed_at: str | None = None
    executive_summary: list[str] = Field(default_factory=list)
    awards: list[HistoricalPurchaseRow] = Field(default_factory=list)
    suppliers: list[PartyShareRow] = Field(default_factory=list)
    concentration: ConcentrationBlock = Field(default_factory=ConcentrationBlock)
    categories: list[CategoryStatRow] = Field(default_factory=list)
    products: list[ProductAwardRow] = Field(default_factory=list)
    price_history: PriceHistoryBlock = Field(default_factory=PriceHistoryBlock)
    frequency: FrequencyBlock = Field(default_factory=FrequencyBlock)
    modalities: list[ModalityStatsRow] = Field(default_factory=list)
    temporal_months: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: float | None = None
    rows_scanned: int = 0
    cache_hit: bool = False
    message: str = ""


class DGCPSupplierCompareRequest(BaseModel):
    keys: list[str] = Field(min_length=1, max_length=3)
    window_months: int | None = 24


class DGCPSupplierCompareRow(BaseModel):
    identity: ProfileIdentity
    awards_count: int
    total_amount: Decimal | None = None
    currency: str = "DOP"
    last_award_date: str | None = None
    institutions_count: int = 0
    categories_count: int = 0
    last_12m_amount: Decimal | None = None


class DGCPSupplierCompareResponse(BaseModel):
    window_months: int | None = None
    rows: list[DGCPSupplierCompareRow] = Field(default_factory=list)
    note: str = "Comparación descriptiva; no es un ranking de calidad ni recomendación."
