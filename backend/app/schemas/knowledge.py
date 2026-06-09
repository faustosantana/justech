"""Schemas — Corporate Knowledge Repository (Fase 7.2)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeHealthResponse(BaseModel):
    enabled: bool
    source_path: str
    source_available: bool
    assets_count: int
    entities_count: int
    alerts_open: int
    last_sync_at: datetime | None
    sync_folders: list[str]
    category_counts: dict[str, int] = Field(default_factory=dict)
    chunks_count: int = 0


class KnowledgeAssetResponse(BaseModel):
    id: UUID
    source_provider: str
    relative_path: str
    folder_category: str
    filename: str
    title: str
    display_name: str
    format: str
    document_type: str
    repository_category: str
    repository_category_label: str
    display_type: str
    display_status: str
    sncc_label: str | None = None
    detected_supplier: str | None = None
    requires_vigency: bool = False
    company_key: str | None
    supplier_name: str | None
    manufacturer_name: str | None
    client_name: str | None
    valid_from: date | None
    valid_until: date | None
    vigency_status: str
    tags: list[str] = Field(default_factory=list)
    synced_at: datetime | None
    analyzed_at: datetime | None


class KnowledgeAssetListResponse(BaseModel):
    items: list[KnowledgeAssetResponse]
    total: int


class KnowledgeSyncResult(BaseModel):
    source_provider: str
    assets_synced: int
    assets_created: int
    assets_updated: int
    entities_created: int
    relationships_created: int
    alerts_created: int
    duration_ms: int
    errors: list[str] = Field(default_factory=list)


class KnowledgeGraphNode(BaseModel):
    id: UUID
    entity_type: str
    slug: str
    name: str
    company_key: str | None = None
    document_count: int = 0


class KnowledgeGraphEdge(BaseModel):
    from_id: UUID
    to_id: UUID
    relationship_type: str
    label: str | None = None


class KnowledgeGraphResponse(BaseModel):
    nodes: list[KnowledgeGraphNode]
    edges: list[KnowledgeGraphEdge]


class KnowledgeVigencyItem(BaseModel):
    asset_id: UUID
    title: str
    document_type: str
    company_key: str | None
    valid_until: date | None
    vigency_status: str
    relative_path: str


class KnowledgeVigencyResponse(BaseModel):
    vigente: list[KnowledgeVigencyItem] = Field(default_factory=list)
    proximo_a_vencer: list[KnowledgeVigencyItem] = Field(default_factory=list)
    vencido: list[KnowledgeVigencyItem] = Field(default_factory=list)
    sin_fecha: list[KnowledgeVigencyItem] = Field(default_factory=list)


class KnowledgeSearchHit(BaseModel):
    asset_id: UUID
    title: str
    document_type: str
    company_key: str | None
    relative_path: str
    snippet: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    query: str
    hits: list[KnowledgeSearchHit]
    total: int
