"""Expedientes automáticos — licitación, cliente, proveedor, legal."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.schemas.document import DocumentExpedienteItem, DocumentExpedienteResponse

EXPEDIENTE_REQUIREMENTS: dict[str, list[tuple[str, str]]] = {
    "licitacion": [
        ("rpe", "RPE vigente"),
        ("registro_mercantil", "Registro Mercantil"),
        ("certificacion_tss", "Certificación TSS"),
        ("certificacion_dgii", "Certificación DGII"),
        ("sncc", "Formulario SNCC"),
        ("propuesta", "Propuesta técnica/económica"),
    ],
    "cliente": [
        ("contrato", "Contrato marco"),
        ("factura", "Facturas recientes"),
        ("cotizacion", "Cotizaciones"),
    ],
    "proveedor": [
        ("cotizacion", "Cotización proveedor"),
        ("contrato", "Acuerdo comercial"),
    ],
    "legal": [
        ("registro_mercantil", "Registro Mercantil"),
        ("certificacion_tss", "Certificación TSS"),
        ("certificacion_dgii", "Certificación DGII"),
        ("rpe", "RPE"),
    ],
}


class DocumentExpedienteService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def build(self, expediente_type: str, subject: str) -> DocumentExpedienteResponse:
        reqs = EXPEDIENTE_REQUIREMENTS.get(expediente_type, [])
        result = await self.db.execute(
            select(Document).where(
                Document.tenant_id == self.tenant_id,
                Document.is_active.is_(True),
            )
        )
        docs = list(result.scalars().all())
        subject_lower = subject.lower()

        items: list[DocumentExpedienteItem] = []
        for req_type, label in reqs:
            match = None
            for doc in docs:
                cat = (doc.category or "").lower()
                tags = " ".join(doc.tags or []).lower()
                kws = " ".join(doc.keywords or []).lower()
                text_blob = f"{doc.title} {doc.filename} {cat} {tags} {kws}".lower()
                if req_type in cat or req_type in text_blob:
                    if subject_lower in text_blob or not subject:
                        match = doc
                        break
            items.append(
                DocumentExpedienteItem(
                    required_type=req_type,
                    label=label,
                    status="presente" if match else "faltante",
                    document_id=match.id if match else None,
                    document_title=match.title if match else None,
                )
            )

        missing = sum(1 for i in items if i.status == "faltante")
        return DocumentExpedienteResponse(
            expediente_type=expediente_type,
            subject=subject,
            items=items,
            complete=missing == 0,
            missing_count=missing,
        )
