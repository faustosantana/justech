"""Search Analytics — eventos y agregados (Fase 6.5)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.search_analytics import SearchAnalyticsEvent
from app.schemas.search import SearchAnalyticsResponse, SearchAnalyticsSummary, SearchTopQuery


class SearchAnalyticsService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def record(
        self,
        *,
        user_id: uuid.UUID | None,
        channel: str,
        query: str,
        latency_ms: int,
        cache_hit: bool,
        index_hit: bool,
        result_count: int,
        sources_used: list[str],
        filters: dict | None = None,
    ) -> None:
        if not settings.search_analytics_enabled:
            return
        event = SearchAnalyticsEvent(
            tenant_id=self.tenant_id,
            user_id=user_id,
            channel=channel,
            query=query[:512],
            filters=filters or {},
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            index_hit=index_hit,
            result_count=result_count,
            sources_used=sources_used,
        )
        self.db.add(event)
        await self.db.flush()

    async def get_analytics(self, *, days: int = 7) -> SearchAnalyticsResponse:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        base = select(SearchAnalyticsEvent).where(
            SearchAnalyticsEvent.tenant_id == self.tenant_id,
            SearchAnalyticsEvent.created_at >= since,
        )

        total_q = select(func.count()).select_from(SearchAnalyticsEvent).where(
            SearchAnalyticsEvent.tenant_id == self.tenant_id,
            SearchAnalyticsEvent.created_at >= since,
        )
        total = (await self.db.execute(total_q)).scalar_one()

        avg_q = select(func.avg(SearchAnalyticsEvent.latency_ms)).where(
            SearchAnalyticsEvent.tenant_id == self.tenant_id,
            SearchAnalyticsEvent.created_at >= since,
        )
        avg_latency = (await self.db.execute(avg_q)).scalar_one() or 0.0

        cache_hits_q = select(func.count()).select_from(SearchAnalyticsEvent).where(
            SearchAnalyticsEvent.tenant_id == self.tenant_id,
            SearchAnalyticsEvent.created_at >= since,
            SearchAnalyticsEvent.cache_hit.is_(True),
        )
        cache_hits = (await self.db.execute(cache_hits_q)).scalar_one()

        index_hits_q = select(func.count()).select_from(SearchAnalyticsEvent).where(
            SearchAnalyticsEvent.tenant_id == self.tenant_id,
            SearchAnalyticsEvent.created_at >= since,
            SearchAnalyticsEvent.index_hit.is_(True),
        )
        index_hits = (await self.db.execute(index_hits_q)).scalar_one()

        top_q = (
            select(
                SearchAnalyticsEvent.query,
                func.count().label("count"),
                func.avg(SearchAnalyticsEvent.latency_ms).label("avg_latency"),
            )
            .where(
                SearchAnalyticsEvent.tenant_id == self.tenant_id,
                SearchAnalyticsEvent.created_at >= since,
            )
            .group_by(SearchAnalyticsEvent.query)
            .order_by(func.count().desc())
            .limit(20)
        )
        top_rows = (await self.db.execute(top_q)).all()

        return SearchAnalyticsResponse(
            days=days,
            summary=SearchAnalyticsSummary(
                total_queries=total,
                avg_latency_ms=round(float(avg_latency), 2),
                cache_hit_ratio=round(cache_hits / total, 4) if total else 0.0,
                index_hit_ratio=round(index_hits / total, 4) if total else 0.0,
            ),
            top_queries=[
                SearchTopQuery(
                    query=row.query,
                    count=row.count,
                    avg_latency_ms=round(float(row.avg_latency), 2),
                )
                for row in top_rows
            ],
        )
