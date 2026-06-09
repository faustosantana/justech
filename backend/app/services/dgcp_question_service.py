"""Consultas DGCP estructuradas para el Assistant."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dgcp_opportunity import DGCPOpportunity
from app.schemas.assistant import AssistantLink, AssistantQueryResponse
from app.services.assistant_actions import table_row
from app.services.assistant_context_policy import is_dgcp_record_question
from app.services.business_answer_builder import build_business_answer, links_to_dict, not_found_summary
from app.services.business_intent_router import ParsedBusinessQuestion
from app.services.business_terms import matches_product_name


class DgcpQuestionService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def answer(self, question: str, parsed: ParsedBusinessQuestion) -> AssistantQueryResponse:
        lowered = question.lower()
        today = date.today()
        week_end = today + timedelta(days=7)

        if is_dgcp_record_question(question, parsed) and not parsed.product_terms:
            return AssistantQueryResponse(
                question=question,
                answer=(
                    "Necesito más información para responder con precisión. "
                    "Abre el detalle de la licitación o indica el código del proceso."
                ),
                sources=["dgcp"],
                query_type="dgcp_query",
            )

        if any(k in lowered for k in ("vencen esta semana", "vencen la semana", "vence esta semana")):
            return await self._deadline_week(question)

        items = await self._search_opportunities(parsed)
        label = parsed.product_label or "licitaciones"

        if not items:
            return AssistantQueryResponse(
                question=question,
                answer=not_found_summary(label, "dgcp", kind="licitaciones"),
                sources=["dgcp"],
                query_type="dgcp_query",
            )

        total_amount = sum((o.amount for o in items), Decimal("0"))
        summary = f"Encontré {len(items)} licitaciones relacionadas con {label} en DGCP."

        metrics = [
            {"label": "Procesos encontrados", "value": str(len(items))},
            {"label": "Monto total", "value": f"{float(total_amount):,.2f}"},
            {"label": "Término buscado", "value": label},
        ]

        rows = []
        for o in items[:15]:
            rows.append(
                table_row(
                    [
                        o.code,
                        (o.title or "")[:60],
                        o.institution[:40] if o.institution else "—",
                        f"{float(o.amount):,.2f}",
                        str(o.deadline),
                        o.status,
                    ],
                    entity_type="dgcp",
                    entity_id=str(o.id),
                )
            )

        links = [AssistantLink(label=o.code, url=f"/dgcp/{o.id}", type="dgcp") for o in items[:10]]
        structured = build_business_answer(
            intent="dgcp_query",
            source="dgcp",
            summary=summary,
            metrics=metrics,
            tables=[
                {
                    "title": "Licitaciones",
                    "columns": ["Código", "Título", "Institución", "Monto", "Vence", "Estado"],
                    "rows": rows,
                }
            ],
            warnings=["Resultados filtrados por título y descripción en DGCP."],
            links=links_to_dict(links),
        )

        return AssistantQueryResponse(
            question=question,
            answer=summary,
            sources=["dgcp"],
            query_type="dgcp_query",
            structured_data=structured,
            links=links,
        )

    async def _search_opportunities(self, parsed: ParsedBusinessQuestion) -> list[DGCPOpportunity]:
        if not parsed.product_terms and not parsed.product_label:
            return []
        stmt = (
            select(DGCPOpportunity)
            .where(DGCPOpportunity.tenant_id == self.tenant_id)
            .order_by(DGCPOpportunity.deadline.asc())
            .limit(20)
        )
        if parsed.product_terms:
            clauses = []
            for term in parsed.product_terms[:6]:
                pattern = f"%{term}%"
                clauses.append(DGCPOpportunity.title.ilike(pattern))
                clauses.append(DGCPOpportunity.description.ilike(pattern))
            stmt = stmt.where(or_(*clauses))
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        if parsed.product_terms:
            items = [
                o for o in items
                if matches_product_name(o.title or "", parsed.product_terms)
                or matches_product_name(o.description or "", parsed.product_terms)
            ]
        return items

    async def _deadline_week(self, question: str) -> AssistantQueryResponse:
        today = date.today()
        week_end = today + timedelta(days=7)
        result = await self.db.execute(
            select(DGCPOpportunity)
            .where(
                DGCPOpportunity.tenant_id == self.tenant_id,
                DGCPOpportunity.deadline >= today,
                DGCPOpportunity.deadline <= week_end,
            )
            .order_by(DGCPOpportunity.deadline.asc())
            .limit(15)
        )
        items = list(result.scalars().all())
        if not items:
            return AssistantQueryResponse(
                question=question,
                answer="No encontré licitaciones que venzan esta semana en DGCP.",
                sources=["dgcp"],
                query_type="dgcp_query",
            )
        summary = f"Hay {len(items)} licitaciones que vencen esta semana."
        rows = [
            table_row(
                [o.code, (o.title or "")[:50], str(o.deadline), o.status],
                entity_type="dgcp",
                entity_id=str(o.id),
            )
            for o in items
        ]
        links = [AssistantLink(label=o.code, url=f"/dgcp/{o.id}", type="dgcp") for o in items[:10]]
        structured = build_business_answer(
            intent="dgcp_query",
            source="dgcp",
            summary=summary,
            metrics=[{"label": "Vencen esta semana", "value": str(len(items))}],
            tables=[{
                "title": "Vencimientos",
                "columns": ["Código", "Título", "Vence", "Estado"],
                "rows": rows,
            }],
            links=links_to_dict(links),
        )
        return AssistantQueryResponse(
            question=question,
            answer=summary,
            sources=["dgcp"],
            query_type="dgcp_query",
            structured_data=structured,
            links=links,
        )
