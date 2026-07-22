from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OpportunityStatus(str, Enum):
    DETECTED = "detected"
    ANALYZING = "analyzing"
    QUALIFIED = "qualified"
    NOT_QUALIFIED = "not_qualified"
    PREPARING = "preparing"
    PENDING_DOCUMENTS = "pending_documents"
    READY_TO_SUBMIT = "ready_to_submit"
    SUBMITTED = "submitted"
    UNDER_EVALUATION = "under_evaluation"
    SUSPENDED = "suspended"
    AWARDED = "awarded"
    LOST = "lost"
    CANCELLED = "cancelled"
    # Legacy — compatibilidad datos existentes (migrados en 049)
    TO_REVIEW = "to_review"
    INTERESTED = "interested"
    TO_BID = "to_bid"
    DISCARDED = "discarded"
    WON = "won"


class OpportunityAction(str, Enum):
    MARCAR_INTERES = "marcar_interes"
    DESMARCAR_INTERES = "desmarcar_interes"
    INICIAR_PREPARACION = "iniciar_preparacion"
    MARCAR_LISTO_PRESENTAR = "marcar_listo_presentar"
    MARCAR_PRESENTADA = "marcar_presentada"
    MARCAR_SUSPENDIDA = "marcar_suspendida"
    MARCAR_ADJUDICADA = "marcar_adjudicada"
    MARCAR_NO_ADJUDICADA = "marcar_no_adjudicada"
    DESCARTAR = "descartar"
    # Legacy aliases
    MOSTRAR_INTERES = "mostrar_interes"
    REVISAR = "revisar"
    LICITAR = "licitar"
    GANADA = "ganada"
    PERDIDA = "perdida"


class OpportunityCompany(str, Enum):
    JUSTECH = "justech"
    JUST_OFFICE = "just_office"
    MF_PLUG_SAFE = "mf_plug_safe"
    OMNI_SOLUTIONS = "omni_solutions"
    UNCLASSIFIED = "unclassified"


class OpportunityPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


ACTION_TO_STATUS: dict[OpportunityAction, OpportunityStatus] = {
    OpportunityAction.MARCAR_INTERES: OpportunityStatus.INTERESTED,
    OpportunityAction.MOSTRAR_INTERES: OpportunityStatus.INTERESTED,
    OpportunityAction.DESMARCAR_INTERES: OpportunityStatus.DETECTED,
    OpportunityAction.REVISAR: OpportunityStatus.DETECTED,
    OpportunityAction.INICIAR_PREPARACION: OpportunityStatus.PREPARING,
    OpportunityAction.LICITAR: OpportunityStatus.PREPARING,
    OpportunityAction.MARCAR_LISTO_PRESENTAR: OpportunityStatus.READY_TO_SUBMIT,
    OpportunityAction.MARCAR_PRESENTADA: OpportunityStatus.SUBMITTED,
    OpportunityAction.MARCAR_SUSPENDIDA: OpportunityStatus.SUSPENDED,
    OpportunityAction.MARCAR_ADJUDICADA: OpportunityStatus.AWARDED,
    OpportunityAction.GANADA: OpportunityStatus.AWARDED,
    OpportunityAction.MARCAR_NO_ADJUDICADA: OpportunityStatus.LOST,
    OpportunityAction.PERDIDA: OpportunityStatus.LOST,
    OpportunityAction.DESCARTAR: OpportunityStatus.DISCARDED,
}


STATUS_LABELS_ES: dict[str, str] = {
    "detected": "Nueva",
    "interested": "Interesada",
    "preparing": "En preparación",
    "ready_to_submit": "Lista para presentar",
    "submitted": "Presentada",
    "under_evaluation": "Presentada (en evaluación)",
    "suspended": "Suspendida",
    "awarded": "Adjudicada",
    "lost": "No adjudicada",
    "discarded": "Descartada",
    "cancelled": "Cancelada",
    "analyzing": "En análisis",
    "qualified": "Calificada",
    "not_qualified": "No calificada",
    "pending_documents": "Pendiente documentos",
    "to_review": "Nueva (requiere revisión)",
    "to_bid": "En preparación",
    "won": "Adjudicada",
}


PIPELINE_STATUSES: list[str] = [
    "detected",
    "interested",
    "preparing",
    "ready_to_submit",
    "submitted",
    "suspended",
    "awarded",
    "lost",
    "discarded",
]


class DGCPOpportunityCreate(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    institution: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1)
    amount: Decimal = Field(ge=0)
    currency: str = "DOP"
    probability: int = Field(ge=0, le=100, default=0)
    score: int = Field(ge=0, le=100, default=0)
    status: OpportunityStatus = OpportunityStatus.DETECTED
    priority: OpportunityPriority = OpportunityPriority.MEDIUM
    company: OpportunityCompany = OpportunityCompany.UNCLASSIFIED
    deadline: date
    description: str | None = None
    modalidad: str | None = None
    source: str = Field(default="manual", max_length=32)
    source_url: str | None = None
    responsible_user_id: UUID | None = None
    full_info: dict[str, Any] = Field(default_factory=dict)
    similar_history: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)
    ai_recommendations: list[str] = Field(default_factory=list)
    suggested_action: str | None = None
    justech_potential_amount: Decimal = Field(ge=0, default=0)


class DGCPOpportunityUpdate(BaseModel):
    status: OpportunityStatus | None = None
    notes: str | None = None


class DGCPOpportunityActionRequest(BaseModel):
    action: OpportunityAction
    notes: str | None = None


class DGCPOpportunityResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    code: str
    ocid: str | None = None
    institution: str
    title: str
    amount: Decimal
    currency: str
    probability: int
    score: int
    status: OpportunityStatus
    priority: OpportunityPriority
    company: OpportunityCompany
    confidence_score: int = 0
    classification_reason: str | None = None
    dgcp_status: str | None = None
    modalidad: str | None = None
    objeto_proceso: str | None = None
    deadline: date
    description: str | None
    source_url: str | None = None
    full_info: dict[str, Any]
    similar_history: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    ai_recommendations: list[str]
    suggested_action: str | None
    jaios_intelligence: dict[str, Any] = Field(default_factory=dict)
    justech_potential_amount: Decimal
    needs_review: bool = False
    funnel_stage: str | None = None
    funnel_stage_label: str | None = None
    status_label: str | None = None
    next_recommended_action: str | None = None
    primary_action: str | None = None
    available_actions: list[str] = Field(default_factory=list)
    responsible_name: str | None = None
    synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DGCPOpportunitySummary(BaseModel):
    total_opportunities: int
    total_potential_amount: Decimal
    by_status: dict[str, int]
    by_company: dict[str, int]
    by_priority: dict[str, int]
    amount_by_company: dict[str, Decimal]
    to_bid: int
    to_review: int
    discarded: int
    won: int
    lost: int
    presentation: dict[str, int] = Field(default_factory=dict)


class DGCPOpportunityListResponse(BaseModel):
    items: list[DGCPOpportunityResponse]
    summary: DGCPOpportunitySummary
    total: int


class DGCPSyncRequest(BaseModel):
    max_pages: int = Field(default=5, ge=1, le=50)
    page_size: int = Field(default=50, ge=1, le=100)


class DGCPSyncJobResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    trigger: str
    status: str
    pages_synced: int
    created_count: int
    updated_count: int
    skipped_count: int
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class DGCPSyncScheduleResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    is_enabled: bool
    interval_hours: int
    max_pages: int
    page_size: int
    last_run_at: datetime | None
    next_run_at: datetime | None

    model_config = {"from_attributes": True}


class DGCPSyncScheduleUpdate(BaseModel):
    is_enabled: bool | None = None
    interval_hours: int | None = Field(default=None, ge=1, le=168)
    max_pages: int | None = Field(default=None, ge=1, le=50)
    page_size: int | None = Field(default=None, ge=1, le=100)


class DGCPOpportunityHistoryResponse(BaseModel):
    id: UUID
    opportunity_id: UUID
    user_id: UUID | None
    action: str
    from_status: str | None
    to_status: str | None
    notes: str | None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_history(cls, row: Any) -> "DGCPOpportunityHistoryResponse":
        return cls(
            id=row.id,
            opportunity_id=row.opportunity_id,
            user_id=row.user_id,
            action=row.action,
            from_status=row.from_status,
            to_status=row.to_status,
            notes=row.notes,
            metadata=row.metadata_,
            created_at=row.created_at,
        )


class DGCPAuditLogResponse(BaseModel):
    id: UUID
    action: str
    resource_type: str | None
    resource_id: UUID | None
    details: dict[str, Any]
    user_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
