"""Schemas — DGCP Requirements & Bid Package (Fase 7.1)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DGCPRequirementEvidence(BaseModel):
    requirement_key: str
    documento_origen: str
    pagina: int | None = None
    seccion: str | None = None
    fragmento: str
    confianza: str
    process_document_id: UUID | None = None


class DGCPRequirementItem(BaseModel):
    key: str
    label: str
    tipo: str
    mandatory: bool = True
    subsanable: bool = False
    source: str = "extracted"
    matched_text: str | None = None
    evidence: list[DGCPRequirementEvidence] = Field(default_factory=list)


class DGCPRequirementsResponse(BaseModel):
    opportunity_id: UUID
    opportunity_code: str
    opportunity_title: str
    analyzed_at: datetime | None
    technical: list[DGCPRequirementItem] = Field(default_factory=list)
    legal: list[DGCPRequirementItem] = Field(default_factory=list)
    financial: list[DGCPRequirementItem] = Field(default_factory=list)
    administrative: list[DGCPRequirementItem] = Field(default_factory=list)
    mandatory_documents: list[DGCPRequirementItem] = Field(default_factory=list)
    subsanable_documents: list[DGCPRequirementItem] = Field(default_factory=list)
    critical_dates: list[dict[str, Any]] = Field(default_factory=list)
    guarantees: list[str] = Field(default_factory=list)
    samples: list[str] = Field(default_factory=list)
    sncc_forms: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class DGCPChecklistItem(BaseModel):
    id: UUID
    requirement_key: str
    requirement: str
    tipo: str
    mandatory: bool
    status: str
    document_id: UUID | None = None
    document_title: str | None = None
    valid_until: date | None = None
    risk: str | None = None
    recommended_action: str | None = None
    assignee: str | None = None
    task_id: UUID | None = None
    completable: bool = False
    form_type: str | None = None
    display_status: str | None = None
    notes: str | None = None
    knowledge_asset_id: UUID | None = None
    relative_path: str | None = None
    match_source: str | None = None
    validity_analysis: dict[str, Any] | None = None
    manual_validation: dict[str, Any] | None = None
    note_history: list[dict[str, Any]] = Field(default_factory=list)


class DGCPChecklistNoteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=4000)


class DGCPChecklistNoteResponse(BaseModel):
    opportunity_id: UUID
    checklist_item_id: UUID
    notes: str | None = None
    note_history: list[dict[str, Any]] = Field(default_factory=list)
    checklist: DGCPChecklistResponse


class DGCPManualValidationRequest(BaseModel):
    status: str
    note: str = ""
    expiration_date: date | None = None
    evidence: str = ""


class DGCPManualValidationResponse(BaseModel):
    opportunity_id: UUID
    checklist_item_id: UUID
    requirement_key: str
    previous_status: str
    new_status: str
    manual_validation: dict[str, Any]
    checklist: DGCPChecklistResponse
    bid_package: DGCPBidPackageResponse
    expediente_status: str


class DGCPAssociateDocumentRequest(BaseModel):
    document_id: UUID | None = None
    knowledge_asset_id: UUID | None = None
    process_document_id: UUID | None = None


class DGCPAssociateDocumentResponse(BaseModel):
    opportunity_id: UUID
    checklist_item_id: UUID
    requirement_key: str
    document_id: UUID | None = None
    knowledge_asset_id: UUID | None = None
    process_document_id: UUID | None = None
    document_title: str | None = None
    match_source: str | None = None
    checklist: DGCPChecklistResponse
    bid_package: DGCPBidPackageResponse
    expediente_status: str


class DGCPDocumentPreviewResponse(BaseModel):
    opportunity_id: UUID
    checklist_item_id: UUID
    requirement_key: str
    requirement_label: str
    document_id: UUID | None = None
    document_title: str | None = None
    knowledge_asset_id: UUID | None = None
    relative_path: str | None = None
    match_source: str | None = None
    extracted_text: str | None = None
    validity_analysis: dict[str, Any] | None = None
    download_url: str | None = None
    preview_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DGCPChecklistResponse(BaseModel):
    opportunity_id: UUID
    items: list[DGCPChecklistItem]
    total: int
    mandatory_total: int = 0
    ready_count: int
    compliant_count: int = 0
    pending_count: int
    expired_count: int
    incomplete_count: int
    review_count: int = 0
    unanalyzed_count: int = 0


class DGCPDocumentMatch(BaseModel):
    requirement_key: str
    requirement_label: str
    document_id: UUID | None
    document_title: str | None
    knowledge_asset_id: UUID | None = None
    match_source: str | None = None
    relative_path: str | None = None
    match_score: float
    status: str
    vigency_status: str | None = None
    valid_until: date | None = None
    notes: str | None = None
    observation: str | None = None
    validity_analysis: dict[str, Any] | None = None


class DGCPDocumentMatchesResponse(BaseModel):
    opportunity_id: UUID
    matches: list[DGCPDocumentMatch]
    found_count: int
    missing_count: int
    expired_count: int
    review_count: int = 0
    complete_count: int = 0


class DGCPBidPackageResponse(BaseModel):
    opportunity_id: UUID
    opportunity_code: str
    preparation_pct: float
    total_requirements: int = 0
    mandatory_requirements: int = 0
    compliant_count: int = 0
    found_documents: int
    pending_documents: int
    expired_documents: int
    forms_to_complete: int
    review_count: int = 0
    recommended_tasks: list[str] = Field(default_factory=list)
    available: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    expired: list[str] = Field(default_factory=list)
    to_complete: list[str] = Field(default_factory=list)
    requires_review: list[str] = Field(default_factory=list)
    analyzed_at: datetime | None = None


class DGCPFormPreviewRequest(BaseModel):
    form_type: str = "SNCC.F042"
    company: str = "justech"


class DGCPFormPreviewField(BaseModel):
    label: str
    value: str | None
    status: str
    confidence: float = 0.0
    source: str | None = None


class DGCPFormPreviewResponse(BaseModel):
    opportunity_id: UUID
    form_type: str
    company: str
    fields: list[DGCPFormPreviewField]
    missing: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    overall_confidence: float = 0.0
    note: str = "Vista previa — no se modifica el archivo original."
    generate_enabled: bool = False


class DGCPAnalyzeResponse(BaseModel):
    opportunity_id: UUID
    requirements: DGCPRequirementsResponse
    checklist: DGCPChecklistResponse
    bid_package: DGCPBidPackageResponse
    document_matches: DGCPDocumentMatchesResponse
    process_documents: list[dict[str, Any]] = Field(default_factory=list)
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    analysis_warnings: list[str] = Field(default_factory=list)
    expediente_status: str = "sin_preparar"


class DGCPProcessDocumentResponse(BaseModel):
    id: UUID
    title: str
    doc_role: str
    priority: str
    format: str
    source_type: str
    source_url: str | None
    ingestion_status: str
    has_text: bool


class DGCPProcessDocumentsResponse(BaseModel):
    opportunity_id: UUID
    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int


class DGCPFormAutofillPreviewResponse(DGCPFormPreviewResponse):
    generate_enabled: bool = True


class DGCPFormGenerateResponse(BaseModel):
    opportunity_id: UUID
    form_type: str
    output_path: str
    filename: str
    fields_completed: int
    fields_pending: int
    overall_confidence: float


class DGCPBidAlertResponse(BaseModel):
    opportunity_id: UUID
    alerts: list[dict[str, Any]]
    total: int


class DGCPExpedientePrepareResponse(BaseModel):
    opportunity_id: UUID
    expediente_status: str
    expediente_path: str
    preparation_pct: float
    copied_documents: int
    generated_forms: int
    manifest: dict[str, Any]


class DGCPBidPackageStatusResponse(BaseModel):
    opportunity_id: UUID
    opportunity_code: str
    expediente_status: str
    expediente_path: str | None
    preparation_pct: float
    total_requirements: int = 0
    mandatory_requirements: int = 0
    compliant_count: int = 0
    found_documents: int
    pending_documents: int
    expired_documents: int
    forms_to_complete: int
    review_count: int = 0
    alerts_count: int
    manifest: dict[str, Any] = Field(default_factory=dict)
    can_mark_ready: bool = False
    can_download: bool = False
    present_enabled: bool = False


class DGCPUserInputRequest(BaseModel):
    fabricante: str | None = None
    plazo_entrega: str | None = None
    garantia: str | None = None
    monto: str | None = None
    notes: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
