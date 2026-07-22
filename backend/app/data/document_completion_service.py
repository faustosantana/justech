"""Autocompletado documental — vista previa con datos corporativos (Fase 7.2)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.licitador_company_profile import LicitadorCompanyProfile
from app.schemas.document import DocumentCompletionPreview
from app.services.company_normalization_service import (
    CANONICAL_ADDRESS,
    canonical_label,
    normalize_company_key,
)
from app.services.company_profile_sync_service import CompanyProfileSyncService

SNCC_FORMS = {
    "SNCC.F042": ("SNCC F042", ("razon_social", "rnc", "direccion", "representante_legal", "telefono", "correo")),
    "SNCC.F047": ("SNCC F047", ("razon_social", "rnc", "direccion", "cuenta_bancaria")),
    "SNCC.F033": ("SNCC F033", ("razon_social", "rnc", "representante_legal")),
}

DGCP_FORMS = {
    "DGCP.CUMPLIMIENTO": ("Cuestionario de cumplimiento", ("razon_social", "rnc", "direccion", "correo")),
}


class DocumentCompletionService:
    def __init__(
        self,
        db: AsyncSession | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self._profiles = self._load_profiles()

    @staticmethod
    def _load_profiles() -> dict:
        path = Path(__file__).resolve().parent.parent / "data" / "company_profiles.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    async def preview(self, *, form_type: str, company_key: str = "justech") -> DocumentCompletionPreview:
        key = normalize_company_key(company_key) or company_key.lower().replace(" ", "_")
        profile: dict[str, str] = {}

        # 1) Perfil documental en BD (fuente principal)
        if self.db and self.tenant_id:
            db_profile = await self._load_db_profile(key)
            profile.update(db_profile)

        # 2) OneDrive / knowledge assets
        if self.db and self.tenant_id:
            from app.services.corporate_knowledge_engine import CorporateKnowledgeEngine

            knowledge_profile = CorporateKnowledgeEngine(self.db, self.tenant_id).get_company_profile(key)
            for field, value in knowledge_profile.items():
                if value and not profile.get(field):
                    profile[field] = str(value)

        # 3) Fallback estático (solo campos faltantes)
        static = dict(
            self._profiles.get(key)
            or self._profiles.get(company_key.lower().replace(" ", "_"))
            or self._profiles.get("justech", {})
        )
        for field, value in static.items():
            if value and not profile.get(field):
                profile[field] = str(value)

        if not profile.get("razon_social"):
            profile["razon_social"] = canonical_label(key)
        if not profile.get("direccion"):
            profile["direccion"] = CANONICAL_ADDRESS

        form_key = form_type.upper().replace(" ", ".")
        form_def = SNCC_FORMS.get(form_key) or DGCP_FORMS.get(form_key)
        if not form_def:
            form_def = (form_type, tuple(profile.keys()))

        _, fields_needed = form_def
        filled: dict[str, str] = {}
        missing: list[str] = []
        for field in fields_needed:
            val = profile.get(field)
            if val:
                filled[field] = str(val)
            else:
                missing.append(field)

        return DocumentCompletionPreview(
            form_type=form_key,
            company=profile.get("razon_social", company_key),
            fields=filled,
            missing_in_source=missing,
        )

    async def _load_db_profile(self, company_key: str) -> dict[str, str]:
        if not self.db or not self.tenant_id:
            return {}
        row = (
            await self.db.execute(
                select(LicitadorCompanyProfile).where(
                    LicitadorCompanyProfile.tenant_id == self.tenant_id,
                    LicitadorCompanyProfile.company_key == company_key,
                )
            )
        ).scalar_one_or_none()
        if not row:
            return {}

        raw = row.raw_json or {}
        normalized = CompanyProfileSyncService._normalize_json(raw)
        profile = {
            "razon_social": canonical_label(company_key),
            "rnc": row.rnc or normalized.get("rnc"),
            "direccion": row.direccion or normalized.get("direccion") or CANONICAL_ADDRESS,
            "telefono": row.telefono or normalized.get("telefono"),
            "correo": row.correo or normalized.get("correo"),
            "representante_legal": row.representante_legal or normalized.get("representante_legal"),
            "cuenta_bancaria": normalized.get("datos_bancarios") or normalized.get("cuenta_bancaria"),
        }
        return {k: str(v) for k, v in profile.items() if v}
