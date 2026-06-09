"""Search Index — indexación y consulta Tasks, Notifications, DGCP."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document
from app.models.knowledge import KnowledgeAsset
from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.notification import Notification
from app.models.search_index import SearchIndexEntry, SearchIndexState
from app.models.task import Task
from app.schemas.search import SearchResultGroup, SearchResultItem
from app.services.enterprise_search_service import EnterpriseSearchService, GROUP_LABELS

INDEX_SOURCES = ("dgcp", "jaios_tasks", "jaios_notifications", "documents", "knowledge")
SYNC_INTERVAL = timedelta(minutes=5)


class SearchIndexService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def ensure_synced(self) -> None:
        if not settings.search_index_enabled:
            return
        now = datetime.now(timezone.utc)
        for source in INDEX_SOURCES:
            state = await self._get_state(source)
            if state and state.last_run_at and (now - state.last_run_at) < SYNC_INTERVAL:
                continue
            try:
                if source == "dgcp":
                    await self._sync_dgcp(now)
                elif source == "jaios_tasks":
                    await self._sync_tasks(now)
                elif source == "jaios_notifications":
                    await self._sync_notifications(now)
                elif source == "documents":
                    await self._sync_documents(now)
                elif source == "knowledge":
                    await self._sync_knowledge(now)
                await self._set_state(source, now, error=None)
            except Exception as exc:
                await self._set_state(source, now, error=str(exc)[:500])

    async def _get_state(self, source: str) -> SearchIndexState | None:
        result = await self.db.execute(
            select(SearchIndexState).where(
                SearchIndexState.tenant_id == self.tenant_id,
                SearchIndexState.source == source,
            )
        )
        return result.scalar_one_or_none()

    async def _set_state(self, source: str, run_at: datetime, *, error: str | None) -> None:
        stmt = insert(SearchIndexState).values(
            tenant_id=self.tenant_id,
            source=source,
            last_run_at=run_at,
            last_error=error,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["tenant_id", "source"],
            set_={"last_run_at": run_at, "last_error": error},
        )
        await self.db.execute(stmt)

    async def _sync_dgcp(self, now: datetime) -> None:
        result = await self.db.execute(
            select(DGCPOpportunity).where(DGCPOpportunity.tenant_id == self.tenant_id)
        )
        rows = list(result.scalars().all())
        active_ids: set[str] = set()
        for row in rows:
            active_ids.add(str(row.id))
            await self._upsert(
                source="dgcp",
                entity_type="licitación",
                entity_id=str(row.id),
                user_id=None,
                title=row.title[:500],
                subtitle=row.institution,
                description=f"Código {row.code} · vence {row.deadline}",
                url=f"/dgcp/{row.id}",
                company=row.company,
                metadata={"code": row.code, "status": row.status},
                source_updated_at=row.synced_at or getattr(row, "updated_at", None),
                indexed_at=now,
            )
        await self._deactivate_missing("dgcp", "licitación", active_ids)

    async def _sync_tasks(self, now: datetime) -> None:
        result = await self.db.execute(select(Task).where(Task.tenant_id == self.tenant_id))
        rows = list(result.scalars().all())
        active_ids: set[str] = set()
        for row in rows:
            active_ids.add(str(row.id))
            await self._upsert(
                source="jaios",
                entity_type="tarea",
                entity_id=str(row.id),
                user_id=None,
                title=row.title,
                subtitle=row.suggested_assignee_name,
                description=row.customer_name or (row.description[:300] if row.description else None),
                url=f"/tasks/{row.id}",
                company=row.department,
                metadata={"status": row.status, "priority": row.priority},
                source_updated_at=row.updated_at,
                indexed_at=now,
            )
        await self._deactivate_missing("jaios", "tarea", active_ids)

    async def _sync_notifications(self, now: datetime) -> None:
        result = await self.db.execute(
            select(Notification).where(Notification.tenant_id == self.tenant_id)
        )
        rows = list(result.scalars().all())
        active_ids: set[str] = set()
        for row in rows:
            active_ids.add(str(row.id))
            await self._upsert(
                source="jaios",
                entity_type="notificación",
                entity_id=str(row.id),
                user_id=row.user_id,
                title=row.title,
                subtitle=row.type,
                description=row.message[:300] if row.message else None,
                url=f"/tasks/{row.related_task_id}" if row.related_task_id else "/notifications",
                company=None,
                metadata={"type": row.type},
                source_updated_at=row.created_at,
                indexed_at=now,
            )
        await self._deactivate_missing("jaios", "notificación", active_ids)

    async def _sync_documents(self, now: datetime) -> None:
        result = await self.db.execute(
            select(Document).where(
                Document.tenant_id == self.tenant_id,
                Document.is_active.is_(True),
            )
        )
        rows = list(result.scalars().all())
        active_ids: set[str] = set()
        for row in rows:
            if not row.indexed_at and not row.extracted_text:
                continue
            active_ids.add(str(row.id))
            summary = ""
            if row.intelligence and isinstance(row.intelligence, dict):
                summary = str(row.intelligence.get("summary", ""))[:500]
            description = (row.extracted_text or "")[:1000] or summary
            await self._upsert(
                source="documents",
                entity_type="document",
                entity_id=str(row.id),
                user_id=None,
                title=row.title,
                subtitle=row.filename,
                description=description,
                url=f"/documents?id={row.id}",
                company=row.company,
                metadata={
                    "category": row.category,
                    "client_name": row.client_name,
                    "supplier_name": row.supplier_name,
                    "tags": list(row.tags or []),
                },
                source_updated_at=row.updated_at,
                indexed_at=now,
            )
        await self._deactivate_missing("documents", "document", active_ids)

    async def _sync_knowledge(self, now: datetime) -> None:
        result = await self.db.execute(
            select(KnowledgeAsset).where(
                KnowledgeAsset.tenant_id == self.tenant_id,
                KnowledgeAsset.is_active.is_(True),
            )
        )
        rows = list(result.scalars().all())
        active_ids: set[str] = set()
        for row in rows:
            active_ids.add(str(row.id))
            description = (row.extracted_text or "")[:1000] or row.relative_path
            await self._upsert(
                source="knowledge",
                entity_type="conocimiento",
                entity_id=str(row.id),
                user_id=self.user_id,
                title=row.title,
                subtitle=row.document_type,
                description=description,
                url=f"/documents?knowledge={row.id}",
                company=row.company_key,
                metadata={
                    "document_type": row.document_type,
                    "relative_path": row.relative_path,
                    "vigency_status": row.vigency_status,
                    "supplier_name": row.supplier_name,
                    "manufacturer_name": row.manufacturer_name,
                },
                source_updated_at=row.updated_at,
                indexed_at=now,
            )
        await self._deactivate_missing("knowledge", "conocimiento", active_ids)

    async def _upsert(
        self,
        *,
        source: str,
        entity_type: str,
        entity_id: str,
        user_id: uuid.UUID | None,
        title: str,
        subtitle: str | None,
        description: str | None,
        url: str,
        company: str | None,
        metadata: dict,
        source_updated_at: datetime | None,
        indexed_at: datetime,
    ) -> None:
        stmt = insert(SearchIndexEntry).values(
            tenant_id=self.tenant_id,
            source=source,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            title=title,
            subtitle=subtitle,
            description=description,
            url=url,
            company=company,
            metadata_=metadata,
            source_updated_at=source_updated_at,
            indexed_at=indexed_at,
            is_active=True,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["tenant_id", "source", "entity_type", "entity_id"],
            set_={
                "title": title,
                "subtitle": subtitle,
                "description": description,
                "url": url,
                "company": company,
                "metadata": metadata,
                "user_id": user_id,
                "source_updated_at": source_updated_at,
                "indexed_at": indexed_at,
                "is_active": True,
            },
        )
        await self.db.execute(stmt)

    async def _deactivate_missing(
        self, source: str, entity_type: str, active_ids: set[str]
    ) -> None:
        result = await self.db.execute(
            select(SearchIndexEntry.entity_id).where(
                SearchIndexEntry.tenant_id == self.tenant_id,
                SearchIndexEntry.source == source,
                SearchIndexEntry.entity_type == entity_type,
                SearchIndexEntry.is_active.is_(True),
            )
        )
        existing = {row[0] for row in result.all()}
        stale = existing - active_ids
        if not stale:
            return
        await self.db.execute(
            delete(SearchIndexEntry).where(
                SearchIndexEntry.tenant_id == self.tenant_id,
                SearchIndexEntry.source == source,
                SearchIndexEntry.entity_type == entity_type,
                SearchIndexEntry.entity_id.in_(stale),
            )
        )

    async def search_groups(
        self,
        query: str,
        *,
        source_filter: str | None,
        type_filter: str | None,
        company_filter: str | None,
        limit_per_group: int,
    ) -> tuple[list[SearchResultGroup], bool]:
        if not settings.search_index_enabled:
            return [], False

        q = query.strip()
        pattern = f"%{q}%"
        base = select(SearchIndexEntry).where(
            SearchIndexEntry.tenant_id == self.tenant_id,
            SearchIndexEntry.is_active.is_(True),
            or_(
                SearchIndexEntry.title.ilike(pattern),
                SearchIndexEntry.subtitle.ilike(pattern),
                SearchIndexEntry.description.ilike(pattern),
            ),
        )

        if source_filter == "dgcp":
            base = base.where(SearchIndexEntry.source == "dgcp")
        elif source_filter == "jaios":
            base = base.where(SearchIndexEntry.source == "jaios")
        elif source_filter == "odoo":
            return [], False
        elif source_filter == "documents":
            base = base.where(SearchIndexEntry.source == "documents")

        result = await self.db.execute(base.limit(limit_per_group * 4))
        rows = list(result.scalars().all())

        grouped: dict[str, list[SearchResultItem]] = {
            "dgcp": [],
            "tasks": [],
            "notifications": [],
            "documents": [],
        }

        for row in rows:
            if row.entity_type == "notificación" and row.user_id != self.user_id:
                continue
            if company_filter and row.company:
                filters = (
                    company_filter.split("|")
                    if "|" in company_filter
                    else [company_filter]
                )
                if not any(
                    f.lower() in row.company.lower() or row.company.lower() in f.lower()
                    for f in filters
                ):
                    continue
            elif company_filter and not row.company:
                continue

            item = SearchResultItem(
                id=row.entity_id,
                type=row.entity_type,
                title=row.title,
                subtitle=row.subtitle,
                description=row.description,
                source=row.source if row.source != "jaios" else "jaios",
                url=row.url,
                company=row.company,
                score=EnterpriseSearchService._score(q, row.title, row.subtitle, row.description)
                + row.score_boost,
                metadata=row.metadata_ or {},
            )
            if row.entity_type == "licitación":
                if type_filter and type_filter not in ("dgcp", "licitación"):
                    continue
                grouped["dgcp"].append(item)
            elif row.entity_type == "tarea":
                if type_filter and type_filter not in ("tasks", "tarea"):
                    continue
                grouped["tasks"].append(item)
            elif row.entity_type == "notificación":
                if type_filter and type_filter not in ("notifications", "notificación"):
                    continue
                grouped["notifications"].append(item)
            elif row.entity_type == "document":
                if type_filter and type_filter not in ("documents", "document", "documento"):
                    continue
                grouped["documents"].append(item)

        groups: list[SearchResultGroup] = []
        for group_type, label_key in (
            ("dgcp", "dgcp"),
            ("tasks", "tasks"),
            ("notifications", "notifications"),
            ("documents", "documents"),
        ):
            items = grouped[group_type]
            if not items:
                continue
            items.sort(key=lambda x: x.score, reverse=True)
            items = items[:limit_per_group]
            groups.append(
                SearchResultGroup(type=group_type, label=GROUP_LABELS[label_key], count=len(items), items=items)
            )

        return groups, bool(groups)

    async def invalidate_tenant_cache(self) -> None:
        from app.services.search_cache_service import SearchCacheService

        await SearchCacheService().invalidate_tenant(self.tenant_id)
