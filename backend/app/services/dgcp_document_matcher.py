"""Matching de requisitos DGCP contra Document Repository (Fase 7.1)."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.services.dgcp_requirements_extractor import ExtractedRequirement

DOC_TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "rpe": ("rpe", "registro de proveedores"),
    "certificacion_tss": ("tss", "certificacion_tss", "certificación tss"),
    "certificacion_dgii": ("dgii", "certificacion_dgii"),
    "registro_mercantil": ("registro_mercantil", "registro mercantil"),
    "sncc_f033": ("sncc", "f033", "f.033"),
    "sncc_f034": ("sncc", "f034", "f.034"),
    "sncc_f042": ("sncc", "f042", "f.042"),
    "sncc_f047": ("sncc", "f047", "f.047"),
    "oferta_economica": ("oferta", "cotizacion", "cotización", "propuesta"),
    "oferta_tecnica": ("propuesta", "oferta técnica", "oferta tecnica"),
    "autorizacion_fabricante": ("fabricante", "autorización", "autorizacion"),
    "ficha_tecnica": ("ficha técnica", "ficha tecnica"),
    "contrato": ("contrato",),
    "factura": ("factura",),
}


class DGCPDocumentMatcher:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def load_documents(self) -> list[Document]:
        """Solo documentos corporativos reutilizables — excluye copias DGCP por proceso."""
        result = await self.db.execute(
            select(Document).where(
                Document.tenant_id == self.tenant_id,
                Document.is_active.is_(True),
                ~Document.title.contains(" — "),
            )
        )
        return list(result.scalars().all())

    def _blob(self, doc: Document) -> str:
        tags = " ".join(doc.tags or [])
        kws = " ".join(doc.keywords or [])
        return f"{doc.title} {doc.filename} {doc.category} {tags} {kws}".lower()

    def match_requirement(
        self,
        req: ExtractedRequirement,
        docs: list[Document],
    ) -> tuple[Document | None, float, str]:
        aliases = DOC_TYPE_ALIASES.get(req.key, (req.key.replace("_", " "),))
        best: Document | None = None
        best_score = 0.0

        for doc in docs:
            blob = self._blob(doc)
            score = 0.0
            if req.key in (doc.category or "").lower():
                score = 95.0
            elif any(alias in blob for alias in aliases):
                score = 80.0
            elif req.key.replace("_", " ") in blob:
                score = 70.0
            if score > best_score:
                best_score = score
                best = doc

        if not best:
            return None, 0.0, "pendiente"

        today = date.today()
        if best.valid_until and best.valid_until < today:
            return best, best_score, "vencido"

        compliance = best.compliance or {}
        if isinstance(compliance, dict) and compliance.get("status") not in (None, "ok"):
            issues = compliance.get("issues") or []
            if issues:
                return best, best_score, "incompleto"

        if req.key.startswith("sncc_"):
            return best, best_score, "completar"

        return best, best_score, "encontrado"

    async def match_all(
        self,
        requirements: list[ExtractedRequirement],
    ) -> list[dict]:
        docs = await self.load_documents()
        matches: list[dict] = []
        for req in requirements:
            doc, score, status = self.match_requirement(req, docs)
            matches.append({
                "requirement_key": req.key,
                "requirement_label": req.label,
                "document_id": str(doc.id) if doc else None,
                "document_title": doc.title if doc else None,
                "match_score": score,
                "status": status,
                "valid_until": str(doc.valid_until) if doc and doc.valid_until else None,
                "notes": self._status_note(status, req),
            })
        return matches

    @staticmethod
    def _status_note(status: str, req: ExtractedRequirement) -> str | None:
        if status == "pendiente":
            return f"Solicitar o registrar: {req.label}"
        if status == "vencido":
            return f"Renovar documento: {req.label}"
        if status == "completar":
            return f"Disponible para vista previa de completado: {req.label}"
        if status == "incompleto":
            return f"Revisar cumplimiento de: {req.label}"
        return None
