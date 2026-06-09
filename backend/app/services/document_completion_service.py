"""Autocompletado documental — vista previa con datos corporativos (Fase 7.2)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.document import DocumentCompletionPreview

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

    def preview(self, *, form_type: str, company_key: str = "justech") -> DocumentCompletionPreview:
        key = company_key.lower().replace(" ", "_")
        profile = dict(self._profiles.get(key) or self._profiles.get("justech", {}))

        if self.db and self.tenant_id:
            from app.services.corporate_knowledge_engine import CorporateKnowledgeEngine

            knowledge_profile = CorporateKnowledgeEngine(self.db, self.tenant_id).get_company_profile(key)
            profile.update({k: v for k, v in knowledge_profile.items() if v})

        form_key = form_type.upper().replace(" ", ".")
        form_def = SNCC_FORMS.get(form_key) or DGCP_FORMS.get(form_key)
        if not form_def:
            form_def = (form_type, tuple(profile.keys()))

        label, fields_needed = form_def
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
