"""Autollenado y generación controlada de formularios DGCP (Fase 7.3)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.dgcp_opportunity import DGCPOpportunity
from app.schemas.dgcp_bid import DGCPFormAutofillPreviewResponse, DGCPFormGenerateResponse, DGCPFormPreviewField
from app.services.corporate_knowledge_engine import CorporateKnowledgeEngine
from app.services.document_completion_service import DocumentCompletionService


class DGCPFormAutofillService:
    FORM_LABELS = {
        "SNCC.F033": "SNCC F.033",
        "SNCC.F042": "SNCC F.042",
        "SNCC.F047": "SNCC F.047",
        "OFERTA.ECONOMICA": "Oferta económica",
        "CARTA.PRESENTACION": "Carta de presentación",
    }

    FIELD_SOURCES = {
        "razon_social": "Repositorio corporativo",
        "rnc": "Repositorio corporativo",
        "direccion": "Repositorio corporativo",
        "representante_legal": "Repositorio corporativo",
        "telefono": "Repositorio corporativo",
        "correo": "Repositorio corporativo",
        "cuenta_bancaria": "Repositorio corporativo",
        "proceso_dgcp": "DGCP",
        "monto": "DGCP / usuario",
        "fabricante": "Usuario / Assistant",
        "plazo_entrega": "Usuario / Assistant",
        "garantia": "Usuario / Assistant",
    }

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.completion = DocumentCompletionService(db=db, tenant_id=tenant_id)
        self.knowledge = CorporateKnowledgeEngine(db, tenant_id)

    async def autofill_preview(
        self,
        opportunity: DGCPOpportunity,
        *,
        form_type: str = "SNCC.F042",
        company: str = "justech",
        user_input: dict | None = None,
    ) -> DGCPFormAutofillPreviewResponse:
        form_key = form_type.upper().replace(" ", ".")
        preview = self.completion.preview(form_type=form_key, company_key=company)
        merged = dict(preview.fields)
        sources: dict[str, str] = {}
        confidences: dict[str, float] = {}

        for key, val in merged.items():
            sources[key] = "Repositorio corporativo / company_profiles"
            confidences[key] = 0.92 if val else 0.0

        extra = self._dgcp_fields(opportunity, user_input or {})
        for key, val in extra.items():
            if val:
                merged[key] = str(val)
                sources[key] = self.FIELD_SOURCES.get(key, "DGCP")
                confidences[key] = 0.88 if key in ("proceso_dgcp", "monto") else 0.75

        field_labels = {
            "razon_social": "Razón social",
            "rnc": "RNC",
            "direccion": "Dirección",
            "representante_legal": "Representante legal",
            "telefono": "Teléfono",
            "correo": "Correo",
            "cuenta_bancaria": "Cuenta bancaria",
            "proceso_dgcp": "Proceso DGCP",
            "monto": "Monto oferta",
            "fabricante": "Fabricante",
            "plazo_entrega": "Plazo de entrega",
            "garantia": "Garantía",
        }

        fields: list[DGCPFormPreviewField] = []
        missing: list[str] = []
        for key, label in field_labels.items():
            val = merged.get(key)
            if val:
                conf = confidences.get(key, 0.8)
                status = "completo" if conf >= 0.85 else "requiere_revision"
                fields.append(DGCPFormPreviewField(
                    label=label,
                    value=str(val),
                    status=status,
                    confidence=conf,
                    source=sources.get(key),
                ))
            else:
                missing.append(label)
                fields.append(DGCPFormPreviewField(
                    label=label,
                    value=None,
                    status="pendiente",
                    confidence=0.0,
                    source=None,
                ))

        overall = sum(f.confidence for f in fields if f.value) / max(len([f for f in fields if f.value]), 1)

        return DGCPFormAutofillPreviewResponse(
            opportunity_id=opportunity.id,
            form_type=form_key,
            company=preview.company,
            fields=fields,
            missing=missing,
            warnings=[f"Campo pendiente: {m}" for m in missing],
            overall_confidence=round(overall, 2),
            generate_enabled=True,
            note="Vista previa — no modifica plantillas originales.",
        )

    async def generate_controlled_copy(
        self,
        opportunity: DGCPOpportunity,
        *,
        form_type: str = "SNCC.F042",
        company: str = "justech",
        user_input: dict | None = None,
        expediente_path: Path | None = None,
    ) -> DGCPFormGenerateResponse:
        preview = await self.autofill_preview(
            opportunity, form_type=form_type, company=company, user_input=user_input
        )
        base = expediente_path or self._expediente_dir(opportunity) / "02_Formularios_SNCC"
        base.mkdir(parents=True, exist_ok=True)

        form_key = preview.form_type.replace(".", "_")
        out_path = base / f"{form_key}_{opportunity.code}.json"
        payload = {
            "form_type": preview.form_type,
            "opportunity_code": opportunity.code,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": "Copia controlada — no modifica plantilla original",
            "fields": [
                {
                    "label": f.label,
                    "value": f.value,
                    "source": f.source,
                    "confidence": f.confidence,
                    "status": f.status,
                }
                for f in preview.fields
            ],
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        return DGCPFormGenerateResponse(
            opportunity_id=opportunity.id,
            form_type=preview.form_type,
            output_path=str(out_path),
            filename=out_path.name,
            fields_completed=sum(1 for f in preview.fields if f.value),
            fields_pending=len(preview.missing),
            overall_confidence=preview.overall_confidence,
        )

    def _dgcp_fields(self, opportunity: DGCPOpportunity, user_input: dict) -> dict[str, str]:
        fields = {
            "proceso_dgcp": f"{opportunity.code} — {opportunity.title[:100]}",
            "monto": f"{float(opportunity.amount):,.2f} {opportunity.currency}",
        }
        for key in ("fabricante", "plazo_entrega", "garantia", "monto", "razon_social", "rnc"):
            if user_input.get(key):
                fields[key] = str(user_input[key])
        return fields

    def _expediente_dir(self, opportunity: DGCPOpportunity) -> Path:
        safe_code = opportunity.code.replace("/", "_")
        return Path(settings.expediente_storage_path) / str(self.tenant_id) / safe_code
