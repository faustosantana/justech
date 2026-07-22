"""Motor de plantillas M365 — autollenado Word/PDF desde repositorio."""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.m365_repository import M365RepositoryFile
from app.schemas.m365_intelligence import (
    M365TemplateField,
    M365TemplateGenerateResponse,
    M365TemplatePreviewResponse,
)
from app.services.document_completion_service import DocumentCompletionService


TEMPLATE_TYPES = {
    "SNCC.F033": "Formulario SNCC F.033",
    "SNCC.F042": "Formulario SNCC F.042",
    "SNCC.F047": "Formulario SNCC F.047",
    "CONTRATO": "Contrato estándar",
    "CARTA": "Carta comercial",
    "PROPUESTA": "Propuesta económica",
    "CERTIFICACION": "Certificación",
}


class M365TemplateService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self._completion = DocumentCompletionService(db=db, tenant_id=tenant_id)

    async def list_templates(self) -> list[dict]:
        result = await self.db.execute(
            select(M365RepositoryFile)
            .where(
                M365RepositoryFile.tenant_id == self.tenant_id,
                M365RepositoryFile.document_category.in_(("plantilla", "formulario")),
                M365RepositoryFile.is_folder.is_(False),
            )
            .order_by(M365RepositoryFile.name)
            .limit(50)
        )
        rows = list(result.scalars().all())
        builtin = [{"id": k, "name": v, "source": "builtin"} for k, v in TEMPLATE_TYPES.items()]
        repo = [
            {
                "id": str(r.id),
                "name": r.name,
                "source": "repository",
                "graph_item_id": r.graph_item_id,
                "category": r.document_category,
            }
            for r in rows
        ]
        return builtin + repo

    async def preview(
        self, *, template_type: str, company_key: str = "justech", extra: dict | None = None
    ) -> M365TemplatePreviewResponse:
        form_key = template_type.upper().replace(" ", ".")
        preview = await self._completion.preview(form_type=form_key, company_key=company_key)
        fields = [
            M365TemplateField(
                key=k,
                label=k.replace("_", " ").title(),
                value=str(v),
                source="Repositorio corporativo",
                confidence=0.9,
            )
            for k, v in preview.fields.items()
        ]
        for k, v in (extra or {}).items():
            fields.append(M365TemplateField(key=k, label=k, value=str(v), source="Usuario", confidence=1.0))

        missing = preview.missing_in_source or []
        return M365TemplatePreviewResponse(
            template_type=form_key,
            template_label=TEMPLATE_TYPES.get(form_key, form_key),
            fields=fields,
            missing_fields=missing,
            generate_enabled=len(missing) == 0 or len(fields) > 0,
        )

    async def generate(
        self, *, template_type: str, company_key: str = "justech", extra: dict | None = None, output_format: str = "docx"
    ) -> M365TemplateGenerateResponse:
        preview = await self.preview(template_type=template_type, company_key=company_key, extra=extra)
        content = self._build_docx(preview)
        filename = f"{preview.template_type.replace('.', '_')}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.docx"
        return M365TemplateGenerateResponse(
            ok=True,
            filename=filename,
            content_base64=__import__("base64").b64encode(content).decode("ascii"),
            format=output_format,
            message=f"Plantilla {preview.template_label} generada",
        )

    def _build_docx(self, preview: M365TemplatePreviewResponse) -> bytes:
        try:
            from docx import Document

            doc = Document()
            doc.add_heading(preview.template_label, 0)
            doc.add_paragraph(f"Generado por JAIOS — {datetime.now(timezone.utc).isoformat()}")
            for field in preview.fields:
                doc.add_paragraph(f"{field.label}: {field.value}")
            buf = io.BytesIO()
            doc.save(buf)
            return buf.getvalue()
        except ImportError:
            lines = [preview.template_label, ""] + [f"{f.label}: {f.value}" for f in preview.fields]
            return "\n".join(lines).encode("utf-8")
