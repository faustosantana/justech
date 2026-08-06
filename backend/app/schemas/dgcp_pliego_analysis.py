"""Schema canónico versionado — análisis profundo de pliego (29 resultados)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


SCHEMA_VERSION = "pliego_analysis.v1"
PROMPT_VERSION = "pliego_stages.v1"

PLIEGO_FIELD_KEYS: tuple[str, ...] = (
    "resumen_ejecutivo",
    "objeto_contratacion",
    "institucion",
    "modalidad",
    "monto_estimado",
    "fecha_limite",
    "cronograma",
    "lugar_entrega",
    "plazo_entrega",
    "condiciones_pago",
    "garantias",
    "experiencia_requerida",
    "requisitos_legales",
    "requisitos_administrativos",
    "requisitos_tecnicos",
    "requisitos_financieros",
    "documentos_solicitados",
    "formularios_requeridos",
    "certificaciones_requeridas",
    "muestras_requeridas",
    "visita_tecnica",
    "criterios_evaluacion",
    "causas_descalificacion",
    "riesgos",
    "pendientes",
    "recomendaciones",
    "preguntas_institucion",
    "decision_sugerida",
    "nivel_confianza",
)

assert len(PLIEGO_FIELD_KEYS) == 29

PLIEGO_UI_SECTIONS: dict[str, tuple[str, ...]] = {
    "Resumen": ("resumen_ejecutivo", "nivel_confianza", "decision_sugerida"),
    "Datos generales": (
        "objeto_contratacion",
        "institucion",
        "modalidad",
        "monto_estimado",
        "fecha_limite",
    ),
    "Cronograma": ("cronograma", "lugar_entrega", "plazo_entrega"),
    "Requisitos": (
        "experiencia_requerida",
        "requisitos_legales",
        "requisitos_administrativos",
        "requisitos_tecnicos",
        "requisitos_financieros",
    ),
    "Documentos solicitados": (
        "documentos_solicitados",
        "formularios_requeridos",
        "certificaciones_requeridas",
        "muestras_requeridas",
        "visita_tecnica",
    ),
    "Garantías y pagos": ("garantias", "condiciones_pago"),
    "Evaluación y descalificación": ("criterios_evaluacion", "causas_descalificacion"),
    "Riesgos": ("riesgos",),
    "Pendientes": ("pendientes",),
    "Recomendaciones": ("recomendaciones",),
    "Preguntas": ("preguntas_institucion",),
    "Decisión sugerida": ("decision_sugerida",),
}

FIELD_LABELS: dict[str, str] = {
    "resumen_ejecutivo": "Resumen ejecutivo",
    "objeto_contratacion": "Objeto de la contratación",
    "institucion": "Institución",
    "modalidad": "Modalidad",
    "monto_estimado": "Monto estimado",
    "fecha_limite": "Fecha límite",
    "cronograma": "Cronograma",
    "lugar_entrega": "Lugar de entrega",
    "plazo_entrega": "Plazo de entrega",
    "condiciones_pago": "Condiciones de pago",
    "garantias": "Garantías",
    "experiencia_requerida": "Experiencia requerida",
    "requisitos_legales": "Requisitos legales",
    "requisitos_administrativos": "Requisitos administrativos",
    "requisitos_tecnicos": "Requisitos técnicos",
    "requisitos_financieros": "Requisitos financieros",
    "documentos_solicitados": "Documentos solicitados",
    "formularios_requeridos": "Formularios requeridos",
    "certificaciones_requeridas": "Certificaciones requeridas",
    "muestras_requeridas": "Muestras requeridas",
    "visita_tecnica": "Visita técnica",
    "criterios_evaluacion": "Criterios de evaluación",
    "causas_descalificacion": "Causas de descalificación",
    "riesgos": "Riesgos",
    "pendientes": "Pendientes",
    "recomendaciones": "Recomendaciones",
    "preguntas_institucion": "Preguntas para la institución",
    "decision_sugerida": "Decisión sugerida",
    "nivel_confianza": "Nivel de confianza",
}


class PliegoAnalysisStatus(StrEnum):
    PENDING = "pending"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    CONSOLIDATING = "consolidating"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"


class PliegoEvidence(BaseModel):
    document_id: str | None = None
    document_name: str = ""
    page: int | None = None
    section: str | None = None
    fragment: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    page_identified: bool = True
    review_required: bool = False

    @model_validator(mode="after")
    def _normalize_page(self) -> PliegoEvidence:
        if self.page is not None and self.page < 1:
            self.page = None
            self.page_identified = False
            self.review_required = True
            self.confidence = min(self.confidence, 0.4)
        if not self.page_identified or self.page is None:
            self.page_identified = False
            self.review_required = True
            if self.confidence > 0.55:
                self.confidence = 0.55
        if self.fragment and len(self.fragment) > 280:
            self.fragment = self.fragment[:277] + "…"
        return self


class PliegoFieldResult(BaseModel):
    key: str
    label: str = ""
    value: Any = "No identificado"
    items: list[Any] = Field(default_factory=list)
    found: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[PliegoEvidence] = Field(default_factory=list)
    source_documents: list[str] = Field(default_factory=list)
    review_required: bool = True
    notes: str = ""
    manual_override: bool = False
    reviewed: bool = False
    comment: str | None = None

    @model_validator(mode="after")
    def _defaults(self) -> PliegoFieldResult:
        if not self.label:
            self.label = FIELD_LABELS.get(self.key, self.key)
        if not self.found:
            if self.value in (None, "", []):
                self.value = "No identificado"
            self.review_required = True
            if self.confidence > 0.35:
                self.confidence = 0.35
        return self


class PliegoDocumentInput(BaseModel):
    document_id: str
    name: str
    doc_type: str = "general"
    content_hash: str | None = None
    pages: int | None = None
    extracted_text_present: bool = False
    extraction_status: str = "pending"
    extraction_errors: list[str] = Field(default_factory=list)
    ocr_used: bool = False
    ocr_confidence: float | None = None
    analyzed_at: datetime | None = None
    duplicate_of: str | None = None


class PliegoStageResult(BaseModel):
    stage: str
    status: Literal["completed", "partial", "failed", "skipped"] = "completed"
    message: str = ""
    duration_ms: int = 0
    error: str | None = None


class PliegoDecisionSuggested(BaseModel):
    decision: Literal["participar", "revisar", "no_participar"] = "revisar"
    reason: str = ""
    positive_factors: list[str] = Field(default_factory=list)
    negative_factors: list[str] = Field(default_factory=list)
    main_risks: list[str] = Field(default_factory=list)
    critical_pendientes: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[PliegoEvidence] = Field(default_factory=list)
    irreversible: bool = False


class PliegoAnalysisMeta(BaseModel):
    schema_version: str = SCHEMA_VERSION
    prompt_version: str = PROMPT_VERSION
    prompt_hash: str = ""
    model: str | None = None
    document_hashes: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    tokens_in: int | None = None
    tokens_out: int | None = None
    estimated_cost_usd: float | None = None
    user_id: str | None = None
    hermes_status: str | None = None
    contradictions: list[str] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    failed_stages: list[str] = Field(default_factory=list)
    llm_enriched: bool = False


class PliegoAnalysisResult(BaseModel):
    opportunity_id: UUID | str
    status: PliegoAnalysisStatus = PliegoAnalysisStatus.PENDING
    version: int = 1
    created_at: datetime | None = None
    fields: dict[str, PliegoFieldResult] = Field(default_factory=dict)
    documents: list[PliegoDocumentInput] = Field(default_factory=list)
    stages: list[PliegoStageResult] = Field(default_factory=list)
    decision: PliegoDecisionSuggested | None = None
    meta: PliegoAnalysisMeta = Field(default_factory=PliegoAnalysisMeta)
    ui_sections: dict[str, list[str]] = Field(default_factory=dict)

    @field_validator("fields")
    @classmethod
    def _ensure_keys(cls, value: dict[str, PliegoFieldResult]) -> dict[str, PliegoFieldResult]:
        out = dict(value or {})
        for key in PLIEGO_FIELD_KEYS:
            if key not in out:
                out[key] = PliegoFieldResult(
                    key=key,
                    label=FIELD_LABELS[key],
                    value="No identificado",
                    found=False,
                    confidence=0.0,
                    review_required=True,
                    notes="Campo no producido por el pipeline; marcado para revisión.",
                )
        return out

    @model_validator(mode="after")
    def _ui(self) -> PliegoAnalysisResult:
        if not self.ui_sections:
            self.ui_sections = {k: list(v) for k, v in PLIEGO_UI_SECTIONS.items()}
        return self

    def ensure_complete_fields(self) -> None:
        for key in PLIEGO_FIELD_KEYS:
            if key not in self.fields:
                self.fields[key] = PliegoFieldResult(
                    key=key,
                    label=FIELD_LABELS[key],
                    value="No identificado",
                    found=False,
                    confidence=0.0,
                    review_required=True,
                )


class PliegoAnalysisVersionSummary(BaseModel):
    version: int
    status: PliegoAnalysisStatus
    created_at: datetime | None = None
    prompt_hash: str = ""
    model: str | None = None
    document_hashes: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    user_id: str | None = None


class PliegoAnalysisResponse(BaseModel):
    opportunity_id: UUID
    current: PliegoAnalysisResult | None = None
    versions: list[PliegoAnalysisVersionSummary] = Field(default_factory=list)


class PliegoFieldReviewRequest(BaseModel):
    reviewed: bool = True
    comment: str | None = None
    corrected_value: Any | None = None
    corrected_items: list[Any] | None = None
