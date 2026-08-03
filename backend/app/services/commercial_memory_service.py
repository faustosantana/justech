"""Memoria comercial — ventas, cotizaciones e histórico unificado."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.price_list import PriceListProduct


class CommercialMemoryService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def query(self, text: str, *, limit: int = 10) -> dict:
        q = (text or "").strip().lower()
        if not q:
            return {"query": text, "results": [], "message": "Indique producto, SKU o cliente."}

        tokens = [t for t in q.split() if len(t) >= 3]
        results: list[dict] = []

        opp_rows = (
            await self.db.execute(
                select(DGCPOpportunity)
                .where(
                    DGCPOpportunity.tenant_id == self.tenant_id,
                    DGCPOpportunity.status.in_(("won", "to_bid", "interested")),
                    or_(
                        *[
                            DGCPOpportunity.title.ilike(f"%{tok}%")
                            for tok in tokens[:5]
                        ]
                    )
                    if tokens
                    else True,
                )
                .order_by(DGCPOpportunity.updated_at.desc())
                .limit(limit)
            )
        ).scalars().all()

        for opp in opp_rows:
            results.append({
                "type": "licitacion",
                "client": opp.institution,
                "date": opp.deadline.isoformat() if opp.deadline else None,
                "amount": str(opp.amount),
                "currency": opp.currency,
                "margin": None,
                "supplier": opp.company,
                "status": opp.status,
                "description": opp.title[:200],
                "reference": opp.code,
            })

        if len(results) < limit:
            prod_q = select(PriceListProduct).where(
                PriceListProduct.tenant_id == self.tenant_id,
                PriceListProduct.is_current.is_(True),
            )
            if tokens:
                prod_q = prod_q.where(
                    or_(
                        *[
                            PriceListProduct.search_blob.ilike(f"%{tok}%")
                            for tok in tokens[:5]
                        ]
                    )
                )
            products = (
                await self.db.execute(prod_q.order_by(PriceListProduct.indexed_at.desc()).limit(limit))
            ).scalars().all()

            for p in products:
                results.append({
                    "type": "catalogo",
                    "client": None,
                    "date": p.source_file_date.isoformat() if p.source_file_date else None,
                    "amount": str(p.preferred_price or p.price or ""),
                    "currency": p.currency,
                    "margin": None,
                    "supplier": p.supplier,
                    "status": "indexado",
                    "description": (p.description or "")[:200],
                    "reference": p.sku or p.mpn,
                })

        answered = len(results) > 0
        return {
            "query": text,
            "has_history": answered,
            "results": results[:limit],
            "message": (
                f"Se encontraron {len(results)} registro(s) relacionados."
                if answered
                else "No hay historial comercial indexado para esta consulta."
            ),
        }
