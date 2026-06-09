"""Enterprise Search — interfaces Fase 6 + Search Acceleration Engine (Fase 6.5, sin implementar)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IndexSource(str, Enum):
    DGCP = "dgcp"
    ODOO = "odoo"
    M365 = "m365"
    DOCUMENTS = "documents"
    TASKS = "tasks"
    NOTIFICATIONS = "notifications"
    MEMORY = "memory"


@dataclass
class SearchHit:
    title: str
    snippet: str
    source: IndexSource
    source_id: str
    score: float = 0.0
    url: str | None = None
    metadata: dict = field(default_factory=dict)


class EnterpriseSearchIndex(ABC):
    """Índice estructurado — implementación futura sobre tabla search_index."""

    @abstractmethod
    async def search(
        self,
        tenant_id: str,
        query: str,
        *,
        source: str | None = None,
        entity_type: str | None = None,
        company: str | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        pass

    @abstractmethod
    async def upsert(
        self,
        tenant_id: str,
        source: IndexSource,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any],
    ) -> None:
        pass

    @abstractmethod
    async def deactivate(self, tenant_id: str, source: IndexSource, entity_id: str) -> None:
        pass

    @abstractmethod
    async def get_watermark(self, tenant_id: str, source: IndexSource) -> str | None:
        pass

    @abstractmethod
    async def set_watermark(self, tenant_id: str, source: IndexSource, watermark: str) -> None:
        pass


class SearchCacheLayer(ABC):
    """Cache Redis por tenant — Fase 6.5."""

    @abstractmethod
    async def get(self, tenant_id: str, cache_key: str) -> dict[str, Any] | None:
        pass

    @abstractmethod
    async def set(
        self,
        tenant_id: str,
        cache_key: str,
        payload: dict[str, Any],
        *,
        ttl_seconds: int,
    ) -> None:
        pass

    @abstractmethod
    async def invalidate_tenant(self, tenant_id: str) -> None:
        pass

    @abstractmethod
    async def get_tenant_cache_version(self, tenant_id: str) -> int:
        pass


@dataclass
class SearchAnalyticsEvent:
    tenant_id: str
    query: str
    channel: str  # ui | assistant | api
    latency_ms: int
    cache_hit: bool = False
    index_hit: bool = False
    result_count: int = 0
    user_id: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    sources_used: list[str] = field(default_factory=list)


class SearchAnalytics(ABC):
    """Métricas de búsqueda — Fase 6.5."""

    @abstractmethod
    async def record(self, event: SearchAnalyticsEvent) -> None:
        pass

    @abstractmethod
    async def top_queries(self, tenant_id: str, *, days: int = 7, limit: int = 20) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def latency_summary(self, tenant_id: str, *, days: int = 7) -> dict[str, float]:
        pass

    @abstractmethod
    async def cache_hit_ratio(self, tenant_id: str, *, hours: int = 24) -> float:
        pass


class SemanticSearchProvider(ABC):
    """Qdrant + embeddings — Fase 7+ (diseño only)."""

    @abstractmethod
    async def semantic_search(
        self,
        tenant_id: str,
        query: str,
        *,
        limit: int = 10,
        sources: list[IndexSource] | None = None,
    ) -> list[SearchHit]:
        pass

    @abstractmethod
    async def index_embedding(
        self,
        tenant_id: str,
        source: IndexSource,
        entity_id: str,
        text: str,
        metadata: dict[str, Any],
    ) -> None:
        pass


class SearchAccelerationOrchestrator(ABC):
    """
    Orquestador Fase 6.5: cache → índice → fallback Fase 6.
    Implementación futura; EnterpriseSearchService delega aquí cuando enabled.
    """

    @abstractmethod
    async def search(
        self,
        tenant_id: str,
        user_id: str,
        query: str,
        *,
        source_filter: str | None = None,
        type_filter: str | None = None,
        company_filter: str | None = None,
        limit_per_group: int = 8,
        channel: str = "api",
    ) -> dict[str, Any]:
        pass
