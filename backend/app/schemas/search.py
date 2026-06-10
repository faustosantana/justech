"""Schemas — Búsqueda empresarial global."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    id: str
    type: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    source: str
    url: str
    company: str | None = None
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResultGroup(BaseModel):
    type: str
    label: str
    count: int
    items: list[SearchResultItem] = Field(default_factory=list)


class EnterpriseSearchResponse(BaseModel):
    query: str
    total: int
    groups: list[SearchResultGroup] = Field(default_factory=list)
    sources_searched: list[str] = Field(default_factory=list)
    future_sources: list[str] = Field(default_factory=list)
    cache_hit: bool = False
    index_hit: bool = False
    latency_ms: int | None = None


class ResolvedEntitySchema(BaseModel):
    entity_id: str
    entity_type: str
    canonical_name: str
    matched_alias: str
    match_kind: str
    confidence: float
    aliases: list[str] = Field(default_factory=list)

    @classmethod
    def from_entity(cls, ent) -> "ResolvedEntitySchema":
        return cls(
            entity_id=ent.entity_id,
            entity_type=ent.entity_type,
            canonical_name=ent.canonical_name,
            matched_alias=ent.matched_alias,
            match_kind=ent.match_kind,
            confidence=ent.confidence,
            aliases=ent.aliases[:8],
        )


class KnowledgeGraphPayload(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


class KnowledgeEngineResponse(EnterpriseSearchResponse):
    resolved_entities: list[ResolvedEntitySchema] = Field(default_factory=list)
    expanded_terms: list[str] = Field(default_factory=list)
    knowledge_graph: KnowledgeGraphPayload | dict[str, Any] = Field(default_factory=dict)
    search_mode: str = "hybrid_entity_bm25"


class SpeechSearchPlaceholder(BaseModel):
    """Arquitectura futura — búsqueda por voz (no implementada)."""
    enabled: bool = False
    provider: str | None = None
    message: str = "speech-to-text disponible en futura versión"


class AssistantKnowledgeSearchRequest(BaseModel):
    question: str
    company_filter: str | None = None


class AssistantKnowledgeSearchResponse(BaseModel):
    question: str
    answer: str
    search: KnowledgeEngineResponse
    entity_focus: ResolvedEntitySchema | None = None


class SearchAnalyticsSummary(BaseModel):
    total_queries: int
    avg_latency_ms: float
    cache_hit_ratio: float
    index_hit_ratio: float


class SearchTopQuery(BaseModel):
    query: str
    count: int
    avg_latency_ms: float


class SearchAnalyticsResponse(BaseModel):
    days: int
    summary: SearchAnalyticsSummary
    top_queries: list[SearchTopQuery] = Field(default_factory=list)
