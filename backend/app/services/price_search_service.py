"""Búsqueda de precios para asistente — delega al índice PriceIntelligence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_list import PriceListFile, PriceListProduct
from app.services.price_intelligence_service import PriceIntelligenceService, PriceSearchFilters


class PriceSearchService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.intelligence = PriceIntelligenceService(db, tenant_id)

    async def search(self, query: str, *, limit: int = 20, **filters) -> dict:
        f = PriceSearchFilters(q=query, limit=limit, **{k: v for k, v in filters.items() if v is not None})
        result = await self.intelligence.search(f)
        return {
            "query": query,
            "total": result.total,
            "items": [p.model_dump() for p in result.items],
        }

    async def best_supplier(self, query: str) -> dict | None:
        result = await self.search(query, limit=5)
        items = result.get("items") or []
        priced = [i for i in items if i.get("preferred_price")]
        if not priced:
            return None
        best = min(priced, key=lambda x: Decimal(str(x["preferred_price"])))
        return {"product": best, "supplier": best.get("supplier"), "price": best.get("preferred_price")}

    async def lists_today(self) -> list[dict]:
        since = datetime.now(UTC) - timedelta(days=1)
        rows = (
            await self.db.execute(
                select(PriceListFile)
                .where(
                    PriceListFile.tenant_id == self.tenant_id,
                    PriceListFile.is_current.is_(True),
                    PriceListFile.indexed_at >= since,
                )
                .order_by(PriceListFile.indexed_at.desc())
            )
        ).scalars().all()
        return [
            {
                "filename": r.filename,
                "supplier": r.supplier,
                "records": r.total_records,
                "indexed_at": r.indexed_at.isoformat() if r.indexed_at else None,
            }
            for r in rows
        ]

    async def price_changes(self, *, days: int = 7) -> list[dict]:
        since = datetime.now(UTC) - timedelta(days=days)
        rows = (
            await self.db.execute(
                select(PriceListProduct)
                .where(
                    PriceListProduct.tenant_id == self.tenant_id,
                    PriceListProduct.is_current.is_(True),
                    PriceListProduct.indexed_at >= since,
                )
                .order_by(PriceListProduct.indexed_at.desc())
                .limit(50)
            )
        ).scalars().all()
        return [
            {
                "description": r.description,
                "brand": r.brand,
                "supplier": r.supplier,
                "price": str(r.preferred_price) if r.preferred_price else None,
                "indexed_at": r.indexed_at.isoformat(),
            }
            for r in rows
        ]
