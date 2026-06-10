"""Hermes Retrieval — capa local de recuperación para Assistant 3.0."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.search import KnowledgeEngineResponse
from app.services.knowledge_engine_service import KnowledgeEngineService


class HermesRetrievalService:
    """Recuperación documental + búsqueda empresarial (Hermes local / índice JAIOS)."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.knowledge = KnowledgeEngineService(db, tenant_id, user_id)

    async def search(self, query: str, *, limit: int = 8) -> KnowledgeEngineResponse:
        return await self.knowledge.search_global(
            query,
            limit_per_group=limit,
            channel="assistant_hermes",
        )
