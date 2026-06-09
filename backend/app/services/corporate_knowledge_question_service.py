"""Assistant — Corporate Knowledge queries (Fase 7.2)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.corporate_knowledge_engine import CorporateKnowledgeEngine


class CorporateKnowledgeQuestionService:
    KNOWLEDGE_SIGNALS = (
        "rpe", "dgii", "tss", "registro mercantil", "sncc", "f042", "f047", "f033",
        "documento legal", "documentos legales", "vencido", "vencidos", "vigente",
        "repositorio", "justechai", "donde está", "dónde está", "tenemos", "fabricante",
        "proveedor vende", "carta fabricante", "expediente", "faltan para",
    )

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.engine = CorporateKnowledgeEngine(db, tenant_id)

    @classmethod
    def is_knowledge_question(cls, question: str) -> bool:
        q = question.lower()
        return any(s in q for s in cls.KNOWLEDGE_SIGNALS)

    async def answer(self, question: str) -> dict:
        q = question.lower()

        if "vencid" in q or "vencen" in q:
            vig = await self.engine.vigencies()
            items = vig.vencido + vig.proximo_a_vencer
            if not items:
                return self._resp("No hay documentos legales vencidos en el repositorio corporativo.")
            lines = [f"- {i.title} ({i.document_type}) — {i.vigency_status}" for i in items[:10]]
            return self._resp("Documentos con alerta de vigencia:\n" + "\n".join(lines))

        doc_type = self._extract_doc_type(q)
        if doc_type:
            assets = await self.engine.find_by_document_type(doc_type, company_key="justech")
            if not assets:
                return self._resp(f"No encontré {doc_type.upper()} en el repositorio corporativo JustechAI.")
            best = assets[0]
            return self._resp(
                f"{doc_type.upper()} de Justech encontrado en repositorio corporativo.\n"
                f"Archivo: {best.relative_path}\n"
                f"Vigencia: {best.vigency_status}"
                + (f" (hasta {best.valid_until})" if best.valid_until else "")
            )

        if "proveedor" in q and any(m in q for m in ("dell", "hp", "lenovo", "microsoft", "fortinet", "canon", "ingram")):
            manufacturer = next(m for m in ("dell", "hp", "lenovo", "microsoft", "fortinet", "canon", "ingram") if m in q)
            result = await self.engine.search(manufacturer, limit=5)
            if not result.hits:
                return self._resp(f"No encontré referencias a {manufacturer.title()} en el repositorio corporativo.")
            lines = [f"- {h.title} ({h.relative_path})" for h in result.hits]
            return self._resp(f"Referencias a {manufacturer.title()}:\n" + "\n".join(lines))

        if "expediente" in q or "faltan" in q:
            return self._resp(
                "Use la pestaña Expediente en el detalle DGCP tras «Analizar requisitos». "
                "JAIOS cruza requisitos con el repositorio corporativo JustechAI automáticamente."
            )

        result = await self.engine.search(question, limit=5)
        if result.hits:
            lines = [f"- {h.title} [{h.document_type}] — {h.relative_path}" for h in result.hits]
            return self._resp("Resultados del repositorio corporativo:\n" + "\n".join(lines))

        health = await self.engine.health()
        if not health.source_available:
            return self._resp(
                f"Repositorio corporativo no disponible en {health.source_path}. "
                "Ejecute POST /knowledge/sync tras montar JustechAI."
            )
        return self._resp(
            "No encontré documentos coincidentes. Ejecute sincronización del repositorio corporativo "
            "con POST /api/v1/knowledge/sync."
        )

    @staticmethod
    def _extract_doc_type(q: str) -> str | None:
        mapping = {
            "rpe": "rpe",
            "dgii": "dgii",
            "tss": "tss",
            "registro mercantil": "registro_mercantil",
            "sncc f042": "sncc_f042",
            "f042": "sncc_f042",
            "sncc f047": "sncc_f047",
            "f047": "sncc_f047",
            "sncc f033": "sncc_f033",
            "f033": "sncc_f033",
        }
        for key, doc_type in mapping.items():
            if key in q:
                return doc_type
        return None

    @staticmethod
    def _resp(answer: str) -> dict:
        return {
            "answer": answer,
            "query_type": "corporate_knowledge_query",
            "sources": ["knowledge_repository"],
        }
