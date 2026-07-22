"""Consultas documentales para JAIOS Assistant."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.assistant import AssistantQueryResponse
from app.services.business_answer_builder import build_business_answer
from app.services.document_completion_service import DocumentCompletionService
from app.services.document_expediente_service import DocumentExpedienteService
from app.services.document_service import DocumentService


class DocumentQuestionService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.docs = DocumentService(db, tenant_id, user_id)
        self.completion = DocumentCompletionService()
        self.expediente = DocumentExpedienteService(db, tenant_id)

    async def answer(self, question: str, *, sub_intent: str | None, search_term: str | None) -> AssistantQueryResponse:
        q = question.strip()
        lowered = q.lower()

        if sub_intent == "completion_preview" or "sncc" in lowered and "f042" in lowered:
            preview = await self.completion.preview(form_type="SNCC.F042")
            summary = f"Vista previa de completado para {preview.form_type} — {preview.company}."
            structured = build_business_answer(
                intent="document_query",
                source="documents",
                summary=summary,
                metrics=[{"label": k, "value": v} for k, v in preview.fields.items()],
                warnings=[preview.note],
            )
            return AssistantQueryResponse(
                question=q,
                answer=summary,
                sources=["documents"],
                query_type="document_query",
                structured_data=structured,
            )

        if "faltan" in lowered and "licit" in lowered:
            exp = await self.expediente.build("licitacion", "")
            summary = (
                f"Expediente de licitación: {exp.missing_count} documento(s) faltante(s)."
                if exp.missing_count
                else "Expediente de licitación completo según documentos registrados."
            )
            rows = [[i.label, i.status, i.document_title or "—"] for i in exp.items]
            structured = build_business_answer(
                intent="document_query",
                source="documents",
                summary=summary,
                tables=[{"title": "Expediente licitación", "columns": ["Requisito", "Estado", "Documento"], "rows": rows}],
            )
            return AssistantQueryResponse(
                question=q,
                answer=summary,
                sources=["documents"],
                query_type="document_query",
                structured_data=structured,
            )

        if "vencen" in lowered and ("certific" in lowered or "mes" in lowered):
            health = await self.docs.health()
            summary = f"Hay {health.alerts_open} alerta(s) de cumplimiento documental abiertas."
            structured = build_business_answer(
                intent="document_query",
                source="documents",
                summary=summary,
                metrics=[
                    {"label": "Alertas abiertas", "value": str(health.alerts_open)},
                    {"label": "Documentos", "value": str(health.documents_count)},
                ],
            )
            return AssistantQueryResponse(
                question=q,
                answer=summary,
                sources=["documents"],
                query_type="document_query",
                structured_data=structured,
            )

        if "vencid" in lowered and "document" in lowered:
            health = await self.docs.health()
            summary = (
                f"Hay {health.alerts_open} alerta(s) de cumplimiento documental abiertas."
                if health.alerts_open
                else "No hay documentos vencidos registrados en el módulo Documentos."
            )
            structured = build_business_answer(
                intent="document_query",
                source="documents",
                summary=summary,
                metrics=[
                    {"label": "Alertas abiertas", "value": str(health.alerts_open)},
                    {"label": "Documentos", "value": str(health.documents_count)},
                ],
            )
            return AssistantQueryResponse(
                question=q,
                answer=summary,
                sources=["documents"],
                query_type="document_query",
                structured_data=structured,
            )

        if "vigente" in lowered and any(k in lowered for k in ("dgii", "rpe", "tss", "registro", "certific")):
            health = await self.docs.health()
            doc_label = next((k.upper() for k in ("dgii", "rpe", "tss") if k in lowered), "documento")
            summary = (
                f"Consulta de vigencia {doc_label}: {health.documents_count} documento(s) en repositorio."
            )
            structured = build_business_answer(
                intent="document_query",
                source="documents",
                summary=summary,
                metrics=[{"label": "Documentos", "value": str(health.documents_count)}],
            )
            return AssistantQueryResponse(
                question=q,
                answer=summary,
                sources=["documents"],
                query_type="document_query",
                structured_data=structured,
            )

        term = search_term or self._extract_term(q)
        if not term:
            return AssistantQueryResponse(
                question=q,
                answer="Indica qué documento o término buscar. Ejemplo: «¿Dónde está el RPE de Justech?»",
                sources=["documents"],
                query_type="document_query",
            )

        results = await self.docs.search_content(term, limit=10)
        if not results.hits:
            return AssistantQueryResponse(
                question=q,
                answer=f"No encontré documentos relacionados con «{term}» en el repositorio.",
                sources=["documents"],
                query_type="document_query",
            )

        summary = f"Encontré {results.total} coincidencia(s) para «{term}» en documentos."
        rows = [
            [h.title, h.snippet, str(h.page_number or "—"), f"{h.score:.0f}"]
            for h in results.hits[:8]
        ]
        structured = build_business_answer(
            intent="document_query",
            source="documents",
            summary=summary,
            metrics=[{"label": "Resultados", "value": str(results.total)}],
            tables=[{
                "title": "Documentos encontrados",
                "columns": ["Documento", "Fragmento", "Página", "Relevancia"],
                "rows": rows,
            }],
        )
        return AssistantQueryResponse(
            question=q,
            answer=summary,
            sources=["documents"],
            query_type="document_query",
            structured_data=structured,
        )

    @staticmethod
    def _extract_term(question: str) -> str | None:
        import re

        patterns = (
            r"(?i)(?:dónde está|donde esta|busca|buscar|muéstrame|muestrame|tenemos)\s+(?:el|la|los|las)?\s*(.+)",
            r"(?i)documentos?\s+(?:de|con|donde aparezca)\s+(.+)",
            r"(?i)contratos?\s+de\s+(.+)",
        )
        for pat in patterns:
            m = re.search(pat, question.strip().rstrip("?"))
            if m:
                return m.group(1).strip().rstrip("?.")
        return None
