"""Search Acceleration Orchestrator — Cache → Index → Enterprise Search."""

from __future__ import annotations

import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.search import EnterpriseSearchResponse, SearchResultGroup
from app.services.enterprise_search_service import EnterpriseSearchService
from app.services.search_analytics_service import SearchAnalyticsService
from app.services.search_cache_service import SearchCacheService
from app.services.search_index_service import SearchIndexService


class SearchAccelerationOrchestrator:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.legacy = EnterpriseSearchService(db, tenant_id, user_id=user_id)
        self.cache = SearchCacheService()
        self.index = SearchIndexService(db, tenant_id, user_id)
        self.analytics = SearchAnalyticsService(db, tenant_id)

    def _cache_params(
        self,
        query: str,
        *,
        source_filter: str | None,
        type_filter: str | None,
        company_filter: str | None,
        limit_per_group: int,
        channel: str,
    ) -> dict:
        return {
            "q": query.strip().lower(),
            "source": source_filter or "",
            "type": type_filter or "",
            "company": company_filter or "",
            "limit": limit_per_group,
            "channel": channel,
            "user": str(self.user_id),
        }

    def _merge_groups(self, *group_lists: list[SearchResultGroup]) -> list[SearchResultGroup]:
        by_type: dict[str, SearchResultGroup] = {}
        for groups in group_lists:
            for group in groups:
                if group.type not in by_type:
                    by_type[group.type] = group
                else:
                    existing = by_type[group.type]
                    seen = {i.id for i in existing.items}
                    merged_items = list(existing.items)
                    for item in group.items:
                        if item.id not in seen:
                            merged_items.append(item)
                            seen.add(item.id)
                    merged_items.sort(key=lambda x: x.score, reverse=True)
                    by_type[group.type] = SearchResultGroup(
                        type=group.type,
                        label=existing.label,
                        count=len(merged_items),
                        items=merged_items,
                    )
        return list(by_type.values())

    async def search(
        self,
        query: str,
        *,
        source_filter: str | None = None,
        type_filter: str | None = None,
        company_filter: str | None = None,
        limit_per_group: int = 8,
        channel: str = "api",
    ) -> EnterpriseSearchResponse:
        q = query.strip()
        if len(q) < 2:
            return EnterpriseSearchResponse(query=q, total=0, groups=[])

        start = time.perf_counter()
        params = self._cache_params(
            q,
            source_filter=source_filter,
            type_filter=type_filter,
            company_filter=company_filter,
            limit_per_group=limit_per_group,
            channel=channel,
        )

        cached = await self.cache.get_response(self.tenant_id, channel=channel, params=params)
        if cached:
            latency = int((time.perf_counter() - start) * 1000)
            payload = {**cached, "cache_hit": True, "latency_ms": latency}
            response = EnterpriseSearchResponse(**payload)
            await self.analytics.record(
                user_id=self.user_id,
                channel=channel,
                query=q,
                latency_ms=latency,
                cache_hit=True,
                index_hit=cached.get("index_hit", False),
                result_count=response.total,
                sources_used=response.sources_searched,
                filters={"source": source_filter, "type": type_filter, "company": company_filter},
            )
            return response

        index_groups: list[SearchResultGroup] = []
        index_hit = False
        if settings.search_index_enabled and source_filter != "odoo":
            await self.index.ensure_synced()
            index_groups, index_hit = await self.index.search_groups(
                q,
                source_filter=source_filter,
                type_filter=type_filter,
                company_filter=company_filter,
                limit_per_group=limit_per_group,
            )

        odoo_groups: list[SearchResultGroup] = []
        sources_searched: list[str] = []

        if source_filter in (None, "odoo"):
            odoo_params = {"q": q.lower(), "limit": limit_per_group}
            odoo_cached = await self.cache.get_slice(
                self.tenant_id, slice_key="odoo", params=odoo_params
            )
            if odoo_cached:
                odoo_groups = [SearchResultGroup(**g) for g in odoo_cached.get("groups", [])]
                sources_searched.append("odoo")
            else:
                odoo_groups, odoo_sources = await self.legacy.search_odoo(
                    q, limit_per_group=limit_per_group, company_filter=company_filter
                )
                if odoo_groups:
                    sources_searched.extend(odoo_sources)
                    await self.cache.set_slice(
                        self.tenant_id,
                        slice_key="odoo",
                        params=odoo_params,
                        payload={"groups": [g.model_dump() for g in odoo_groups]},
                        ttl_seconds=settings.search_cache_odoo_ttl_seconds,
                    )

        fallback_groups: list[SearchResultGroup] = []
        if not index_hit and source_filter != "odoo":
            if source_filter in (None, "dgcp") and not any(g.type == "dgcp" for g in index_groups):
                dgcp_params = {"q": q.lower(), "limit": limit_per_group}
                dgcp_cached = await self.cache.get_slice(
                    self.tenant_id, slice_key="dgcp", params=dgcp_params
                )
                if dgcp_cached:
                    fallback_groups.extend(
                        [SearchResultGroup(**g) for g in dgcp_cached.get("groups", [])]
                    )
                    if "dgcp" not in sources_searched:
                        sources_searched.append("dgcp")
                else:
                    dgcp_g = await self.legacy.search_dgcp_direct(
                        q, limit_per_group=limit_per_group, company_filter=company_filter
                    )
                    if dgcp_g:
                        fallback_groups.append(dgcp_g)
                        sources_searched.append("dgcp")
                        await self.cache.set_slice(
                            self.tenant_id,
                            slice_key="dgcp",
                            params=dgcp_params,
                            payload={"groups": [dgcp_g.model_dump()]},
                            ttl_seconds=settings.search_cache_dgcp_ttl_seconds,
                        )

            if source_filter in (None, "jaios"):
                has_tasks = any(g.type == "tasks" for g in index_groups)
                has_notif = any(g.type == "notifications" for g in index_groups)
                if not has_tasks or not has_notif:
                    jaios_gs = await self.legacy.search_jaios_direct(
                        q,
                        limit_per_group=limit_per_group,
                        include_tasks=not has_tasks,
                        include_notifications=not has_notif,
                    )
                    fallback_groups.extend(jaios_gs)
                    if jaios_gs and "jaios" not in sources_searched:
                        sources_searched.append("jaios")

        if index_hit:
            index_sources = {item.source for g in index_groups for item in g.items}
            for src in index_sources:
                if src not in sources_searched:
                    sources_searched.append(src)

        groups = self._merge_groups(index_groups, odoo_groups, fallback_groups)
        total = sum(g.count for g in groups)
        latency = int((time.perf_counter() - start) * 1000)

        response = EnterpriseSearchResponse(
            query=q,
            total=total,
            groups=groups,
            sources_searched=list(dict.fromkeys(sources_searched)),
            future_sources=["m365", "qdrant", "hermes"],
            cache_hit=False,
            index_hit=index_hit,
            latency_ms=latency,
        )

        await self.cache.set_response(
            self.tenant_id,
            channel=channel,
            params=params,
            payload=response.model_dump(mode="json"),
        )
        await self.analytics.record(
            user_id=self.user_id,
            channel=channel,
            query=q,
            latency_ms=latency,
            cache_hit=False,
            index_hit=index_hit,
            result_count=total,
            sources_used=response.sources_searched,
            filters={"source": source_filter, "type": type_filter, "company": company_filter},
        )
        return response
