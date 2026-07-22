"""Schemas — expediente real DGCP (Fase 3 / 3.5)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RealExpedienteGenerateResponse(BaseModel):
    opportunity_id: uuid.UUID
    status: str
    expediente_path: str
    zip_filename: str
    preparation_pct: float = 0
    files_count: int = 0
    missing_count: int = 0
    ready_to_upload_count: int = 0
    manifest: dict[str, Any] = Field(default_factory=dict)
    message: str = ""


class RealExpedienteStatusResponse(BaseModel):
    opportunity_id: uuid.UUID
    opportunity_code: str
    status: str = "sin_generar"
    operational_stage: str = "PENDIENTE_REVISION"
    expediente_status: str = "sin_preparar"
    expediente_path: str | None = None
    zip_filename: str | None = None
    preparation_pct: float = 0
    generated_at: datetime | None = None
    folder_counts: dict[str, int] = Field(default_factory=dict)
    missing: list[dict[str, Any]] = Field(default_factory=list)
    expired: list[dict[str, Any]] = Field(default_factory=list)
    requires_review: list[dict[str, Any]] = Field(default_factory=list)
    ready_to_upload: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    can_download: bool = False
    can_mark_ready_review: bool = False
    can_mark_ready_upload: bool = False
    presentation_enabled: bool = False
    presentation_expediente: str = "Pendiente"
    presentation_package: str = "Pendiente"
    presentation_zip: str = "No disponible"
    presentation_upload: str = "Pendiente manual"


class PresentationDashboardSummary(BaseModel):
    sin_generar: int = 0
    expediente_generado: int = 0
    paquete_preparado: int = 0
    listo_para_subir: int = 0
    requiere_actualizacion: int = 0


class RealExpedienteValidationResponse(BaseModel):
    opportunity_id: uuid.UUID
    preparation_pct: float = 0
    general_status: str = "sin_generar"
    completed: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    expired: list[str] = Field(default_factory=list)
    pending_review: list[str] = Field(default_factory=list)
    critical_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    can_prepare_package: bool = False
    manifest_generated: bool = False
