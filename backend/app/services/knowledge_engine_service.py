"""Knowledge Engine Service — orquestador Fase 4 (Entity + Hybrid + Graph)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.search import (
    EnterpriseSearchResponse,
    KnowledgeEngineResponse,
    ResolvedEntitySchema,
    SearchResultGroup,
)
from app.services.enterprise_knowledge_graph import EnterpriseKnowledgeGraph
from app.services.entity_resolution_engine import EntityResolutionEngine
from app.services.hybrid_search_scorer import HybridSearchScorer
from app.services.search_acceleration_orchestrator import SearchAccelerationOrchestrator


class KnowledgeEngineService:
    """Cerebro corporativo — no busca solo texto, resuelve entidades primero."""

    @staticmethod
    def pick_orchestrator_query(query: str, entities: list) -> str:
        """Una sola consulta al orquestador; alias/expand solo al rerank híbrido."""
        q = query.strip()
        if not entities:
            return q
        top = entities[0]
        if top.confidence < 0.65:
            return q

        q_norm = q.lower()
        candidates: list[str] = [q]
        if top.matched_alias:
            candidates.append(top.matched_alias.strip())
        for alias in top.aliases or []:
            if alias:
                candidates.append(str(alias).strip())
        if top.canonical_name:
            candidates.append(top.canonical_name.strip())

        best = q
        for candidate in candidates:
            if len(candidate) < 2:
                continue
            c_norm = candidate.lower()
            if q_norm not in c_norm and c_norm not in q_norm and q_norm.split()[0] not in c_norm:
                continue
            if len(candidate.split()) > len(best.split()) or (
                len(candidate.split()) == len(best.split()) and len(candidate) > len(best)
            ):
                best = candidate
        return best

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.resolver = EntityResolutionEngine(db, tenant_id)
        self.scorer = HybridSearchScorer()
        self.orchestrator = SearchAccelerationOrchestrator(db, tenant_id, user_id)

    async def search_global(
        self,
        query: str,
        *,
        source_filter: str | None = None,
        type_filter: str | None = None,
        company_filter: str | None = None,
        limit_per_group: int = 8,
        channel: str = "knowledge_engine",
    ) -> KnowledgeEngineResponse:
        q = query.strip()
        if len(q) < 2:
            return KnowledgeEngineResponse(
                query=q,
                total=0,
                groups=[],
                search_mode="hybrid_entity_bm25",
            )

        await self.resolver.load()
        entities = self.resolver.resolve(query)
        expanded = self.resolver.expand_search_terms(query, entities)
        orchestrator_query = self.pick_orchestrator_query(query, entities)

        partial = await self.orchestrator.search(
            orchestrator_query,
            source_filter=source_filter,
            type_filter=type_filter,
            company_filter=company_filter,
            limit_per_group=limit_per_group,
            channel=channel,
        )
        cache_hit = partial.cache_hit
        index_hit = partial.index_hit
        latency_ms = partial.latency_ms or 0
        sources = list(partial.sources_searched)

        merged_groups: dict[str, SearchResultGroup] = {}
        for group in partial.groups:
            reranked = self.scorer.rerank_items(
                group.items, query, entities=entities, expanded_terms=expanded
            )
            merged_groups[group.type] = SearchResultGroup(
                type=group.type,
                label=group.label,
                count=len(reranked),
                items=reranked[:limit_per_group],
            )

        groups = sorted(merged_groups.values(), key=lambda g: max((i.score for i in g.items), default=0), reverse=True)
        base = EnterpriseSearchResponse(
            query=query.strip(),
            total=sum(g.count for g in groups),
            groups=groups,
            sources_searched=list(dict.fromkeys(sources)),
            future_sources=["m365_email", "speech_to_text"],
            cache_hit=cache_hit,
            index_hit=index_hit,
            latency_ms=latency_ms or None,
        )

        graph = EnterpriseKnowledgeGraph.build(query=query, entities=entities, response=base)

        return KnowledgeEngineResponse(
            **base.model_dump(),
            resolved_entities=[ResolvedEntitySchema.from_entity(e) for e in entities],
            expanded_terms=expanded,
            knowledge_graph=graph,
            search_mode="hybrid_entity_bm25",
        )

    async def search_entities(self, query: str, *, limit: int = 10) -> list[ResolvedEntitySchema]:
        await self.resolver.load()
        return [ResolvedEntitySchema.from_entity(e) for e in self.resolver.resolve(query, limit=limit)]

    async def search_by_type(
        self,
        query: str,
        group_type: str,
        *,
        limit: int = 8,
    ) -> KnowledgeEngineResponse:
        return await self.search_global(query, type_filter=group_type, limit_per_group=limit)
