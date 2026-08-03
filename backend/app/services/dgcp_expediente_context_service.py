"""Bootstrap de contexto histórico + comercial al abrir expediente DGCP (Fase 1)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.dgcp_opportunity import DGCPOpportunity
from app.schemas.dgcp_expediente_context import (
    DGCPCommercialContextPayload,
    DGCPCommercialSimilarItem,
    DGCPExpedienteContextBootstrapRequest,
    DGCPExpedienteContextResponse,
)
from app.schemas.dgcp_historical import DGCPHistoricalSimilarSearchRequest
from app.services.commercial_index_search_service import CommercialIndexSearchService
from app.services.dgcp_historical_similar_search_service import (
    DGCPHistoricalSimilarSearchService,
    ELIGIBLE_STATUSES,
)
from app.services.dgcp_service import DGCPService

HISTORICAL_BOOTSTRAP_TIMEOUT_SEC = 20.0


class DGCPExpedienteContextService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def bootstrap(
        self,
        opportunity_id: uuid.UUID,
        request: DGCPExpedienteContextBootstrapRequest | None = None,
    ) -> DGCPExpedienteContextResponse:
        request = request or DGCPExpedienteContextBootstrapRequest()
        if not settings.dgcp_auto_expediente_context:
            return DGCPExpedienteContextResponse(
                enabled=False,
                opportunity_id=str(opportunity_id),
                historical_status="disabled",
                commercial_status="disabled",
                error_message="Auto-contexto de expediente deshabilitado (DGCP_AUTO_EXPEDIENTE_CONTEXT=false).",
            )

        dgcp = DGCPService(self.db)
        opportunity = await dgcp.get_opportunity(self.tenant_id, opportunity_id)
        now = datetime.now(UTC).isoformat()

        commercial_task = asyncio.create_task(self._bootstrap_commercial(opportunity))
        historical_task = asyncio.create_task(
            self._bootstrap_historical(opportunity, refresh=request.refresh)
        )

        async def _await_historical() -> tuple[str, str | None, object | None]:
            try:
                return await asyncio.wait_for(historical_task, timeout=HISTORICAL_BOOTSTRAP_TIMEOUT_SEC)
            except asyncio.TimeoutError:
                historical_task.cancel()
                return await self._historical_timeout_fallback(opportunity)

        raw_commercial, raw_historical = await asyncio.gather(
            commercial_task,
            _await_historical(),
            return_exceptions=True,
        )

        if isinstance(raw_commercial, Exception):
            commercial_result: tuple[str, str | None, object | None] = ("error", str(raw_commercial), None)
        else:
            commercial_result = raw_commercial

        if isinstance(raw_historical, Exception):
            historical_result = ("error", str(raw_historical), None)
        else:
            historical_result = raw_historical

        resp = DGCPExpedienteContextResponse(
            enabled=True,
            opportunity_id=str(opportunity_id),
            bootstrap_at=now,
        )

        if isinstance(historical_result, Exception):
            resp.historical_status = "error"
            resp.historical_message = str(historical_result)
        else:
            resp.historical_status, resp.historical_message, resp.historical = historical_result

        if isinstance(commercial_result, Exception):
            resp.commercial_status = "error"
            resp.commercial_message = str(commercial_result)
        else:
            resp.commercial_status, resp.commercial_message, resp.commercial = commercial_result

        if resp.historical_status in ("error", "timeout") and resp.commercial_status == "error":
            resp.error_message = "No se pudo cargar histórico ni comercial Odoo."

        return resp

    async def _historical_timeout_fallback(
        self,
        opportunity: DGCPOpportunity,
    ) -> tuple[str, str | None, object | None]:
        """Devuelve caché parcial si existe; nunca timeout silencioso."""
        service = DGCPHistoricalSimilarSearchService(self.db, self.tenant_id)
        cached = await service.get_cached(opportunity.id)
        if cached.searched_at and cached.total_matches > 0:
            return (
                "partial",
                "Histórico incompleto — resultado parcial en caché. Use «Reanalizar histórico».",
                cached,
            )
        if cached.searched_at and cached.status not in ("pending", "error"):
            return (
                "partial",
                "La búsqueda histórica tardó demasiado. Resultado en caché parcial. Use «Reanalizar histórico».",
                cached,
            )
        return (
            "timeout",
            "La búsqueda histórica tardó demasiado. Use «Reanalizar histórico».",
            cached if cached.searched_at else None,
        )

    async def _bootstrap_historical(
        self,
        opportunity: DGCPOpportunity,
        *,
        refresh: bool,
    ) -> tuple[str, str | None, object | None]:
        if opportunity.status not in ELIGIBLE_STATUSES:
            return (
                "skipped",
                "Marque «Mostrar interés» para habilitar histórico automático.",
                None,
            )

        service = DGCPHistoricalSimilarSearchService(self.db, self.tenant_id)
        if not refresh:
            cached = await service.get_cached(opportunity.id)
            if cached.searched_at and cached.status not in ("pending", "error"):
                return ("done", "Resultado en caché.", cached)

            institution_cached = await service.get_institution_cache(
                opportunity.institution,
                opportunity.id,
            )
            if institution_cached and institution_cached.total_matches > 0:
                return ("done", "Resultado en caché (institución).", institution_cached)

        try:
            result = await service.search_bootstrap(
                opportunity.id,
                DGCPHistoricalSimilarSearchRequest(refresh=refresh, limit=10, max_pages=5),
            )
            if result.status == "error":
                return ("error", result.message or "Error consultando histórico.", result)
            if result.status == "partial":
                return (
                    "partial",
                    result.message or "Histórico incompleto — resultado parcial.",
                    result,
                )
            status = "done"
            message = result.message or None
            return (status, message, result)
        except Exception as exc:
            return ("error", f"Error consultando histórico: {exc}", None)

    async def _bootstrap_commercial(
        self,
        opportunity: DGCPOpportunity,
    ) -> tuple[str, str | None, DGCPCommercialContextPayload]:
        query = " ".join(
            filter(
                None,
                [
                    opportunity.institution,
                    opportunity.title,
                    opportunity.objeto_proceso,
                    opportunity.description,
                ],
            )
        ).strip()

        commercial_svc = CommercialIndexSearchService(self.db, self.tenant_id)
        commercial, price_history = await asyncio.gather(
            commercial_svc.search(query, limit=20),
            commercial_svc.price_history(query=query, limit=15),
        )

        quote_types = {"quotation", "sale_order"}
        sale_types = {"invoice", "sale_order"}

        quotes: list[DGCPCommercialSimilarItem] = []
        sales: list[DGCPCommercialSimilarItem] = []

        for item in commercial.items:
            payload = DGCPCommercialSimilarItem(
                id=str(item.id),
                document_type=item.document_type,
                document_number=item.document_number,
                product_name=item.product_name or item.description,
                customer_name=item.customer_name,
                unit_price=str(item.unit_price) if item.unit_price is not None else None,
                currency=item.currency,
                date=item.date.isoformat() if item.date else None,
                salesperson=item.salesperson,
                margin=str(item.margin) if item.margin is not None else None,
                margin_pct=str(item.margin_pct) if item.margin_pct is not None else None,
                relevance_score=float(item.relevance_score or 0),
            )
            if item.document_type in quote_types:
                quotes.append(payload)
            if item.document_type in sale_types:
                sales.append(payload)

        last_sold = None
        if price_history.items:
            sorted_items = sorted(
                price_history.items,
                key=lambda x: x.date or "",
                reverse=True,
            )
            if sorted_items[0].unit_price is not None:
                last_sold = str(sorted_items[0].unit_price)

        payload = DGCPCommercialContextPayload(
            query=query,
            total=commercial.total,
            index_available=commercial.index_available,
            message=commercial.message,
            quotes=quotes[:10],
            sales=sales[:10],
            last_sold_price=last_sold,
            avg_sold_price=str(price_history.avg_price) if price_history.avg_price else None,
            min_price=str(price_history.min_price) if price_history.min_price else None,
            max_price=str(price_history.max_price) if price_history.max_price else None,
            currency=price_history.items[0].currency if price_history.items else "DOP",
        )
        return ("done", None, payload)
