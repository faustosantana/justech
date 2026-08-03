"""Integración profunda Odoo + DGCP + precios + Hermes — Fase 5."""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dgcp_opportunity import DGCPOpportunity
from app.services.commercial_index_search_service import CommercialIndexSearchService
from app.services.dgcp_form_autofill_service import DGCPFormAutofillService


class IntegratedCommercialFlowService:
    """Orquesta análisis comercial para una licitación u oportunidad."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.commercial = CommercialIndexSearchService(db, tenant_id)
        self.autofill = DGCPFormAutofillService(db, tenant_id)

    async def analyze_opportunity(self, opportunity: DGCPOpportunity) -> dict:
        """Respuesta rápida (<2s): Odoo + precios + inteligencia ya persistida (sin Hermes live)."""
        query = f"{opportunity.institution} {opportunity.title} {opportunity.objeto_proceso or ''}".strip()
        commercial, price_history = await asyncio.gather(
            self.commercial.search(query, limit=15),
            self.commercial.price_history(query=query, limit=10),
        )

        intelligence = opportunity.jaios_intelligence if opportunity.jaios_intelligence else None
        recommendations = self._build_recommendations(
            commercial=commercial,
            price_history=price_history,
            intelligence=intelligence,
            autofill_missing=None,
        )

        return self._payload(
            opportunity=opportunity,
            commercial=commercial,
            price_history=price_history,
            intelligence=intelligence,
            autofill_missing=[],
            can_generate=False,
            recommendations=recommendations,
            enriched=False,
        )

    async def enrich_opportunity(self, opportunity: DGCPOpportunity) -> dict:
        """Enriquecimiento en segundo plano: autofill preview (sin re-ejecutar Hermes)."""
        query = f"{opportunity.institution} {opportunity.title} {opportunity.objeto_proceso or ''}".strip()
        commercial, price_history = await asyncio.gather(
            self.commercial.search(query, limit=15),
            self.commercial.price_history(query=query, limit=10),
        )

        intelligence = opportunity.jaios_intelligence if opportunity.jaios_intelligence else None
        autofill_missing: list[str] = []
        can_generate = False
        try:
            preview = await self.autofill.autofill_preview(opportunity, form_type="SNCC.F042")
            autofill_missing = list(preview.missing or [])
            can_generate = bool(preview.generate_enabled)
        except Exception:
            pass

        recommendations = self._build_recommendations(
            commercial=commercial,
            price_history=price_history,
            intelligence=intelligence,
            autofill_missing=autofill_missing or None,
        )

        return self._payload(
            opportunity=opportunity,
            commercial=commercial,
            price_history=price_history,
            intelligence=intelligence,
            autofill_missing=autofill_missing,
            can_generate=can_generate,
            recommendations=recommendations,
            enriched=True,
        )

    def _build_recommendations(
        self,
        *,
        commercial,
        price_history,
        intelligence: dict | None,
        autofill_missing: list[str] | None,
    ) -> list[str]:
        recommendations: list[str] = []
        if commercial.items:
            recommendations.append(
                f"Encontré {commercial.total} registros comerciales en Odoo relacionados con este proceso."
            )
        if price_history.min_price and price_history.max_price:
            recommendations.append(
                f"Precios históricos indexados entre {price_history.min_price} y {price_history.max_price}."
            )
        if intelligence and isinstance(intelligence, dict):
            recs = intelligence.get("recommendations")
            if isinstance(recs, list):
                recommendations.extend(str(r) for r in recs[:3])
            elif isinstance(recs, dict):
                recommendations.extend(str(v) for v in list(recs.values())[:3])
        if autofill_missing:
            recommendations.append(
                f"Puedo autollenar formularios, pero faltan: {', '.join(autofill_missing)}."
            )
        recommendations.append("Todas las acciones de envío, creación o modificación requieren su aprobación.")
        return recommendations

    def _payload(
        self,
        *,
        opportunity: DGCPOpportunity,
        commercial,
        price_history,
        intelligence: dict | None,
        autofill_missing: list[str],
        can_generate: bool,
        recommendations: list[str],
        enriched: bool,
    ) -> dict:
        return {
            "opportunity_id": str(opportunity.id),
            "code": opportunity.code,
            "enriched": enriched,
            "commercial_search": {
                "total": commercial.total,
                "items": [i.model_dump(mode="json") for i in commercial.items[:8]],
                "target_category": commercial.target_category,
            },
            "price_history": {
                "total": price_history.total,
                "min": str(price_history.min_price) if price_history.min_price else None,
                "max": str(price_history.max_price) if price_history.max_price else None,
                "avg": str(price_history.avg_price) if price_history.avg_price else None,
            },
            "intelligence": intelligence,
            "autofill": {
                "missing": autofill_missing,
                "can_generate": can_generate,
            },
            "recommendations": recommendations,
            "suggested_actions": [
                {"action": "search_history", "label": "Buscar historial", "requires_approval": False},
                {"action": "create_checklist", "label": "Generar checklist", "requires_approval": True},
                {"action": "autofill_document", "label": "Autollenar SNCC F.042", "requires_approval": True},
                {"action": "prepare_proposal", "label": "Preparar borrador propuesta", "requires_approval": True},
            ],
            "sources": [
                {"system": "odoo", "type": "commercial_index", "count": commercial.total},
                {"system": "dgcp", "type": "opportunity", "id": str(opportunity.id)},
            ],
        }
