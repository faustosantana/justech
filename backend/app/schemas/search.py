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
