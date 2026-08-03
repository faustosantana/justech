"""Inteligencia de cotizaciones — contexto histórico y sugerencias (+ Hermes)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.hermes import HermesEmailRfqContext
from app.services.commercial_memory_service import CommercialMemoryService
from app.services.hermes_orchestrator import HermesOrchestrator


class QuotationIntelligenceService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, *, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.memory = CommercialMemoryService(db, tenant_id)

    async def analyze_email(
        self,
        *,
        subject: str,
        body: str,
        client_hint: str | None = None,
        products_hint: list[str] | None = None,
    ) -> dict:
        hermes_result = None
        if settings.hermes_enabled:
            hermes_result = await HermesOrchestrator(
                self.db, self.tenant_id, user_id=self.user_id
            ).analyze_quotation_email(
                HermesEmailRfqContext(subject=subject, body=body, from_address=client_hint),
                module="cotizaciones",
            )

        blob = f"{subject} {body}".lower()
        client = client_hint or (hermes_result.metadata.get("client_hint") if hermes_result else None)
        if not client:
            for token in ("banco", "ministerio", "hospital", "ayuntamiento", "corporación"):
                if token in blob:
                    client = token.title()
                    break

        product_query = " ".join(products_hint or []) or subject
        memory = await self.memory.query(product_query, limit=5)

        similar_quote = None
        for r in memory.get("results") or []:
            if r.get("type") == "licitacion" and r.get("client"):
                similar_quote = r
                break

        similar_message = None
        if similar_quote:
            client_name = similar_quote.get("client") or "cliente"
            date_str = similar_quote.get("date") or "fecha desconocida"
            similar_message = f"Existe actividad similar para {client_name} (ref. {similar_quote.get('reference')}, {date_str})."

        suggested_margin = 15.0
        if similar_quote and similar_quote.get("amount"):
            suggested_margin = 18.0

        products_detected = products_hint or []
        if hermes_result and hermes_result.items_detected:
            products_detected = [
                str(i.get("name") or i) for i in hermes_result.items_detected if i
            ]

        next_actions = hermes_result.next_actions if hermes_result else [
            "Buscar productos en listas indexadas",
            "Preparar borrador de cotización",
            "Validar stock y plazo con proveedor",
        ]

        return {
            "client": client,
            "products_detected": products_detected,
            "similar_quote": similar_quote,
            "similar_message": similar_message,
            "suggested_margin_pct": suggested_margin,
            "memory_hits": memory.get("results") or [],
            "next_actions": next_actions,
            "hermes": hermes_result.model_dump(mode="json") if hermes_result else None,
            "priority": hermes_result.priority if hermes_result else "media",
            "summary": hermes_result.summary if hermes_result else None,
            "analyzed_at": datetime.now(UTC).isoformat(),
        }

    async def find_similar_quotes(self, *, client: str, product: str, months: int = 12) -> list[dict]:
        memory = await self.memory.query(f"{client} {product}", limit=10)
        cutoff = datetime.now(UTC) - timedelta(days=months * 30)
        out = []
        for r in memory.get("results") or []:
            if r.get("date"):
                try:
                    dt = datetime.fromisoformat(r["date"].replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                    if dt >= cutoff:
                        out.append(r)
                except ValueError:
                    out.append(r)
            else:
                out.append(r)
        return out
