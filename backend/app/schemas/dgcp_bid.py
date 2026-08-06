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
    process_document_id: UUID | None = None
    odoo_quotation_id: int | None = None
    odoo_quotation_name: str | None = None
    economic_offer_meta: dict[str, Any] | None = None
    validity_analysis: dict[str, Any] | None = None
    manual_validation: dict[str, Any] | None = None
    note_history: list[dict[str, Any]] = Field(default_factory=list)
    unified_status: str | None = None
    category: str | None = None
    priority: str | None = None
    source_document: str | None = None
    source_page: int | None = None
    source_section: str | None = None
    evidence_fragment: str | None = None
    evidence_confidence: str | None = None
    suggested_document: str | None = None
    ia_observations: str | None = None


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


class DGCPLinkM365DocumentRequest(BaseModel):
    item_id: str
    drive_id: str | None = None
    source_type: str = "onedrive"
    site_id: str | None = None
    name: str | None = None
    web_url: str | None = None
    path: str | None = None


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
    web_url: str | None = None
    view_mode: str | None = None
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
    area_preparation_pct: float | None = None
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
    field_overrides: dict[str, str] = Field(default_factory=dict)
    draft: bool = False


class DGCPFormPreviewField(BaseModel):
    label: str
    value: str | None
    status: str
    confidence: float = 0.0
    source: str | None = None
    key: str | None = None


class DGCPAliasMappingField(BaseModel):
    alias: str
    alias_normalized: str
    canonical: str | None = None
    canonical_label: str | None = None
    value: str | None = None
    source: str | None = None
    confidence: float = 0.0
    status: str = "pendiente"
    mapping_source: str = "unresolved"
    automatic: bool = True
    suggested_canonical: str | None = None
    pending_class: str = "no_critico"


class DGCPAliasFieldSummary(BaseModel):
    total: int = 0
    completed: int = 0
    critical_pending: int = 0
    non_critical_pending: int = 0
    ignored: int = 0
    not_applicable_stage: int = 0


class DGCPAliasMappingSaveRequest(BaseModel):
    alias_normalized: str
    alias_original: str | None = None
    canonical: str | None = None
    value: str | None = None
    scope: str = "global"  # global | template | document
    template_key: str | None = None
    opportunity_id: UUID | None = None
    status: str = "mapeado"  # mapeado | ignorado
    confidence: float = 0.95


class DGCPFormPreviewResponse(BaseModel):
    opportunity_id: UUID
    form_type: str
    company: str
    fields: list[DGCPFormPreviewField]
    missing: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    overall_confidence: float = 0.0
    note: str = "Vista previa — no se modifica el archivo original."
    document_preview_available: bool = False
    template_source: str | None = None
    template_source_type: str | None = None
    pdf_engine: str | None = None
    template_m365: dict | None = None
    alias_fields: list[DGCPAliasMappingField] = Field(default_factory=list)
    alias_summary: DGCPAliasFieldSummary | None = None
    can_pass: bool = False
    ready_for_signature: bool = False
    generate_enabled: bool = False
    draft_enabled: bool = True
    completion_status: str = "PARTIAL"
    aliases_detected: int = 0
    aliases_mapped: int = 0
    critical_pending_aliases: list[str] = Field(default_factory=list)
    non_critical_pending_aliases: list[str] = Field(default_factory=list)


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
    pliego_analysis: dict[str, Any] | None = None


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
    portal: dict[str, Any] | None = None


class DGCPProcessDocumentRoleUpdate(BaseModel):
    doc_role: str


class DGCPProcessDocumentLinkRequest(BaseModel):
    url: str
    title: str | None = None
    doc_role: str = "pliego"


class DGCPProcessDocumentsRefreshResponse(BaseModel):
    opportunity_id: UUID
    discovered: int = 0
    downloaded: int = 0
    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    portal: dict[str, Any] | None = None
    message: str | None = None


class DGCPProcessDocumentUploadResponse(BaseModel):
    opportunity_id: UUID
    process_document: dict[str, Any]
    text_extracted: bool
    text_length: int = 0
    message: str | None = None


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
    docx_path: str | None = None
    pdf_path: str | None = None
    audit_path: str | None = None
    template_hash: str | None = None
    generated_at: str | None = None
    template_source_type: str | None = None
    pdf_engine: str | None = None
    template_m365: dict | None = None
    ready_for_signature: bool = False
    completion_status: str = "DRAFT_OK"
    is_draft: bool = False


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
