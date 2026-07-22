"""Autollenado inteligente DGCP — formularios requeridos y campos faltantes (Fase 3)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.dgcp_bid_package import DGCPBidPackage
from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.licitador_company_profile import LicitadorCompanyProfile
from app.schemas.dgcp_autofill import (
    DGCPAutofillFieldStatus,
    DGCPMissingFieldItem,
    DGCPMissingFieldsResponse,
    DGCPRequiredFormItem,
    DGCPRequiredFormsResponse,
    DGCPResolveMissingFieldRequest,
    DGCPResolveMissingFieldResponse,
)
from app.services.dgcp_form_autofill_service import DGCPFormAutofillService
from app.services.dgcp_expediente_sync_service import DGCPExpedienteSyncService
from app.services.document_autofill.field_alias_registry import canonical_field_key, partition_fields_by_canonical
from app.services.document_autofill.form_template_registry import default_form_type_from_checklist

PROFILE_FIELD_COLUMNS = {
    "razon_social": "razon_social",
    "nombre_comercial": "nombre_comercial",
    "rnc": "rnc",
    "direccion": "direccion",
    "telefono": "telefono",
    "correo": "correo",
    "representante_legal": "representante_legal",
    "representante_autorizado": "representante_legal",
    "cargo": "cargo_representante",
    "cargo_representante": "cargo_representante",
    "cedula_representante": "cedula_representante",
}

LIBRARY_CATEGORIES = frozenset({
    "sncc_formulario",
    "carta",
    "declaracion",
    "contrato",
    "legal_reutilizable",
    "datos_empresa",
    "general_dgcp",
})


class DGCPSmartAutofillService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.forms = DGCPFormAutofillService(db, tenant_id, user_id=user_id)

    @staticmethod
    def enabled() -> bool:
        return bool(settings.dgcp_smart_autofill)

    async def _get_package(self, opportunity_id: uuid.UUID) -> DGCPBidPackage | None:
        row = (
            await self.db.execute(
                select(DGCPBidPackage).where(
                    DGCPBidPackage.tenant_id == self.tenant_id,
                    DGCPBidPackage.opportunity_id == opportunity_id,
                )
            )
        ).scalar_one_or_none()
        return row

    async def _get_opportunity(self, opportunity_id: uuid.UUID) -> DGCPOpportunity | None:
        return await self.db.get(DGCPOpportunity, opportunity_id)

    async def list_required_forms(
        self,
        opportunity_id: uuid.UUID,
        *,
        company: str = "justech",
    ) -> DGCPRequiredFormsResponse:
        if not self.enabled():
            return DGCPRequiredFormsResponse(opportunity_id=opportunity_id)

        pkg = await self._get_package(opportunity_id)
        generated_by_form: dict[str, dict] = {}
        for entry in pkg.generated_forms if pkg else []:
            if isinstance(entry, dict) and entry.get("form_type"):
                generated_by_form[str(entry["form_type"]).upper()] = entry

        required: list[DGCPRequiredFormItem] = []
        seen: set[str] = set()
        for item in pkg.checklist if pkg else []:
            form_type = item.get("form_type")
            if not form_type:
                continue
            key = form_type.upper()
            if key in seen:
                continue
            seen.add(key)
            gen = generated_by_form.get(key)
            if gen:
                status = "borrador_generado" if gen.get("is_draft") else "generado"
            elif item.get("status") in ("requiere_revision", "encontrado_vigente", "validado_manual"):
                status = item.get("display_status") or item.get("status") or "detectado"
            elif item.get("status") == "requiere_completado":
                status = "pendiente_completar"
            else:
                status = item.get("unified_status") or item.get("status") or "pendiente"
            required.append(
                DGCPRequiredFormItem(
                    form_type=form_type,
                    label=self.forms.FORM_LABELS.get(key, form_type),
                    requirement_key=item.get("requirement_key"),
                    status=status,
                    source="process",
                )
            )

        library_forms: list[dict] = []
        from app.services.dgcp_bid_package_service import DGCPBidPackageService

        bid_svc = DGCPBidPackageService(self.db, self.tenant_id, user_id=self.user_id)
        templates = await bid_svc.list_autofill_templates()
        required_keys = {r.form_type.upper() for r in required}
        for tpl in templates:
            ft = (tpl.get("form_type") or "").upper()
            cat = tpl.get("detected_category") or ""
            if ft in required_keys:
                continue
            if cat in LIBRARY_CATEGORIES or not required:
                library_forms.append(tpl)

        return DGCPRequiredFormsResponse(
            opportunity_id=opportunity_id,
            required_forms=required,
            library_forms=library_forms,
        )

    async def _resolve_form_type(
        self,
        opportunity_id: uuid.UUID,
        form_type: str | None,
        *,
        company: str = "justech",
    ) -> str:
        if form_type:
            return form_type
        pkg = await self._get_package(opportunity_id)
        from_checklist = default_form_type_from_checklist(pkg.checklist if pkg else None)
        if from_checklist:
            return from_checklist
        required = await self.list_required_forms(opportunity_id, company=company)
        if required.required_forms:
            return required.required_forms[0].form_type
        raise ValueError("Seleccione un tipo de formulario (form_type)")

    async def missing_fields(
        self,
        opportunity_id: uuid.UUID,
        *,
        form_type: str | None = None,
        company: str = "justech",
    ) -> DGCPMissingFieldsResponse:
        if not self.enabled():
            return DGCPMissingFieldsResponse(
                opportunity_id=opportunity_id,
                form_type=form_type or "",
                company=company,
            )

        form_type = await self._resolve_form_type(opportunity_id, form_type, company=company)

        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")

        pkg = await self._get_package(opportunity_id)
        user_input = dict(pkg.user_input or {}) if pkg else {}
        preview = await self.forms.autofill_preview(
            opportunity,
            form_type=form_type,
            company=company,
            user_input=user_input,
        )

        completed_raw, pending_raw = partition_fields_by_canonical(preview.fields)

        completed_items: list[DGCPAutofillFieldStatus] = []
        for field in completed_raw:
            completed_items.append(
                DGCPAutofillFieldStatus(
                    key=field.key or canonical_field_key(field.label),
                    label=field.label,
                    value=field.value,
                    source=field.source,
                    status=field.status or "completo",
                    confidence=field.confidence,
                )
            )

        items: list[DGCPMissingFieldItem] = []
        for field in pending_raw:
            status = field.status or "pendiente"
            inferred_value, confidence, source = await self._infer_field(
                opportunity,
                field.key,
                company,
                user_input,
                preview.fields,
                form_type=form_type,
            )
            persist_targets = ["expediente"]
            col = PROFILE_FIELD_COLUMNS.get(field.key) or PROFILE_FIELD_COLUMNS.get(
                canonical_field_key(field.key)
            )
            if col:
                persist_targets.append("perfil_empresarial")
            items.append(
                DGCPMissingFieldItem(
                    key=field.key,
                    label=field.label,
                    status=status,
                    suggested_source=source or field.source,
                    can_infer=bool(inferred_value),
                    inferred_value=inferred_value or field.value,
                    inference_confidence=confidence,
                    persist_targets=persist_targets,
                )
            )

        return DGCPMissingFieldsResponse(
            opportunity_id=opportunity_id,
            form_type=form_type,
            company=company,
            fields=items,
            completed_fields=completed_items,
            complete_count=len(completed_items),
            pending_count=len(items),
        )

    async def resolve_missing_field(
        self,
        opportunity_id: uuid.UUID,
        data: DGCPResolveMissingFieldRequest,
        *,
        form_type: str | None = None,
        company: str = "justech",
    ) -> DGCPResolveMissingFieldResponse:
        if not self.enabled():
            raise ValueError("Autollenado inteligente desactivado")

        form_type = await self._resolve_form_type(opportunity_id, form_type, company=company)

        pkg = await self._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")

        merged = dict(pkg.user_input or {})
        merged[data.key] = data.value
        pkg.user_input = merged
        persisted_profile = False

        if data.persist_to_profile:
            persisted_profile = await self._persist_profile_field(company, data.key, data.value)

        persisted_expediente = False
        if data.persist_to_expediente:
            persisted_expediente = True
            checklist = [dict(i) for i in (pkg.checklist or [])]
            for item in checklist:
                if item.get("form_type") == form_type and item.get("status") == "requiere_completado":
                    item["status"] = "requiere_revision"
            pkg.checklist = checklist
            if settings.dgcp_unified_expediente:
                bid = pkg.bid_package or {}
                prep = float(bid.get("preparation_pct") or 0)
                DGCPExpedienteSyncService.sync_package(pkg, checklist=checklist, preparation_pct=prep)

            from app.services.dgcp_expediente_event_service import DGCPExpedienteEventService

            await DGCPExpedienteEventService.publish(
                pkg,
                event_type="missing_field_resolved",
                actor_id=self.user_id,
                detail={"key": data.key, "persisted_profile": persisted_profile},
                checklist=checklist,
            )

        await self.db.commit()

        missing = await self.missing_fields(opportunity_id, form_type=form_type, company=company)
        return DGCPResolveMissingFieldResponse(
            opportunity_id=opportunity_id,
            key=data.key,
            value=data.value,
            persisted_profile=persisted_profile,
            persisted_expediente=persisted_expediente,
            missing_fields=missing,
        )

    async def _persist_profile_field(self, company_key: str, field_key: str, value: str) -> bool:
        column = PROFILE_FIELD_COLUMNS.get(field_key)
        if not column:
            return False
        row = (
            await self.db.execute(
                select(LicitadorCompanyProfile).where(
                    LicitadorCompanyProfile.tenant_id == self.tenant_id,
                    LicitadorCompanyProfile.company_key == company_key,
                )
            )
        ).scalar_one_or_none()
        if not row:
            row = LicitadorCompanyProfile(tenant_id=self.tenant_id, company_key=company_key)
            self.db.add(row)
        setattr(row, column, value)
        raw = dict(row.raw_json or {})
        raw[field_key] = value
        row.raw_json = raw
        return True

    async def _infer_field(
        self,
        opportunity: DGCPOpportunity,
        key: str,
        company: str,
        user_input: dict,
        preview_fields: list,
        *,
        form_type: str,
    ) -> tuple[str | None, float | None, str | None]:
        from app.services.document_autofill.document_autofill_service import DocumentAutofillService

        values: dict[str, str] = {}
        doc_svc = DocumentAutofillService(self.db, self.tenant_id, user_id=self.user_id)
        try:
            resolved = await doc_svc.resolve_values(
                opportunity,
                form_type=form_type,
                company=company,
                user_input=user_input,
            )
            values.update({k: str(v) for k, v in resolved.items() if v})
        except Exception:
            pass

        canon = canonical_field_key(key)
        for f in preview_fields:
            if getattr(f, "key", None) and getattr(f, "value", None):
                values[str(f.key)] = str(f.value)
                values[canonical_field_key(str(f.key))] = str(f.value)

        raw = values.get(key) or values.get(canon)
        if not raw:
            return None, None, None

        source = "Perfil / expediente"
        confidence = 0.92 if key in ("razon_social", "rnc", "direccion") else 0.85
        if key in user_input:
            confidence = 0.98
            source = "Expediente (usuario)"
        elif key in ("proceso_dgcp", "entidad_contratante", "objeto_proceso", "monto", "fecha"):
            confidence = 0.95
            source = "DGCP / sistema"
        return raw, confidence, source
