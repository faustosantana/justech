"""Acciones masivas — Documents, Tasks, Quote Drafts."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import JAIOSException
from app.models.document import Document
from app.models.price_list import PriceQuoteDraft
from app.models.task import Task
from app.schemas.bulk_actions import BulkActionResult
from app.services.company_scope_filter import CompanyScopeFilter
from app.services.task_service import TaskService


class BulkActionsService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.scope = CompanyScopeFilter(db, tenant_id, user_id)
        self.tasks = TaskService(db, tenant_id, user_id)

    async def _load_documents(self, ids: list[uuid.UUID]) -> list[Document]:
        result = await self.db.execute(
            select(Document).where(
                Document.tenant_id == self.tenant_id,
                Document.id.in_(ids),
                Document.is_active.is_(True),
            )
        )
        docs = list(result.scalars().all())
        clause = await self.scope.document_company_clause(Document.company)
        if clause is not None:
            scoped = await self.db.execute(
                select(Document.id).where(
                    Document.tenant_id == self.tenant_id,
                    Document.id.in_(ids),
                    clause,
                )
            )
            allowed = {row[0] for row in scoped.all()}
            docs = [d for d in docs if d.id in allowed]
        return docs

    async def documents_bulk(self, ids: list[uuid.UUID], action: str) -> BulkActionResult:
        docs = await self._load_documents(ids)
        if not docs:
            return BulkActionResult(action=action, affected=0, message="Sin documentos en el scope activo.")

        if action == "archive":
            for doc in docs:
                doc.is_active = False
            await self.db.commit()
            return BulkActionResult(action=action, affected=len(docs), message=f"{len(docs)} documento(s) archivados.")

        if action == "mark_review":
            for doc in docs:
                meta = dict(doc.metadata_ or {})
                meta["review_flagged_at"] = datetime.now(timezone.utc).isoformat()
                doc.metadata_ = meta
            await self.db.commit()
            return BulkActionResult(action=action, affected=len(docs), message=f"{len(docs)} marcados para revisión.")

        if action == "export":
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["id", "title", "company", "category", "client_name", "filename"])
            for doc in docs:
                writer.writerow([str(doc.id), doc.title, doc.company or "", doc.category, doc.client_name or "", doc.filename])
            return BulkActionResult(
                action=action,
                affected=len(docs),
                message=f"Exportados {len(docs)} documentos.",
                export_csv=buf.getvalue(),
            )

        if action == "create_task":
            created = 0
            company_id = await self.scope.primary_company_id()
            for doc in docs:
                from app.schemas.tasks import TaskCreateRequest

                from app.models.work_enums import TaskCategory

                await self.tasks.create_task(
                    TaskCreateRequest(
                        title=f"Revisar documento: {doc.title[:120]}",
                        description=f"Documento {doc.filename}",
                        category=TaskCategory.DOCUMENTO.value,
                        related_document_id=str(doc.id),
                        company_id=company_id,
                    )
                )
                created += 1
            await self.db.commit()
            return BulkActionResult(action=action, affected=created, message=f"{created} tarea(s) creadas.")

        raise JAIOSException(f"Acción no soportada: {action}", code="BULK_UNSUPPORTED")

    async def _load_tasks(self, ids: list[uuid.UUID]) -> list[Task]:
        q = select(Task).where(Task.tenant_id == self.tenant_id, Task.id.in_(ids))
        q = await self.tasks.apply_company_scope(q)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def tasks_bulk(
        self,
        ids: list[uuid.UUID],
        action: str,
        *,
        status: str | None = None,
        priority: str | None = None,
        assigned_to_id: uuid.UUID | None = None,
    ) -> BulkActionResult:
        tasks = await self._load_tasks(ids)
        if not tasks:
            return BulkActionResult(action=action, affected=0, message="Sin tareas en el scope activo.")

        if action == "status" and status:
            for t in tasks:
                t.status = status
            await self.db.commit()
            return BulkActionResult(action=action, affected=len(tasks), message=f"Estado actualizado en {len(tasks)} tareas.")

        if action == "priority" and priority:
            for t in tasks:
                t.priority = priority
            await self.db.commit()
            return BulkActionResult(action=action, affected=len(tasks), message=f"Prioridad actualizada en {len(tasks)} tareas.")

        if action == "assign" and assigned_to_id:
            for t in tasks:
                t.assigned_to_id = assigned_to_id
            await self.db.commit()
            return BulkActionResult(action=action, affected=len(tasks), message=f"Asignadas {len(tasks)} tareas.")

        if action == "archive":
            for t in tasks:
                t.status = "cancelada"
            await self.db.commit()
            return BulkActionResult(action=action, affected=len(tasks), message=f"{len(tasks)} tarea(s) archivadas.")

        raise JAIOSException(f"Acción no soportada: {action}", code="BULK_UNSUPPORTED")

    async def drafts_bulk(
        self,
        ids: list[uuid.UUID],
        action: str,
        *,
        status: str | None = None,
        assigned_user_id: uuid.UUID | None = None,
    ) -> BulkActionResult:
        from app.models.task import Task

        q = select(PriceQuoteDraft).where(
            PriceQuoteDraft.tenant_id == self.tenant_id,
            PriceQuoteDraft.id.in_(ids),
        )
        clause = await self.scope.task_company_clause(Task.company_id)
        if clause is not None:
            q = q.outerjoin(Task, PriceQuoteDraft.task_id == Task.id).where(
                or_(PriceQuoteDraft.task_id.is_(None), clause)
            )
        result = await self.db.execute(q)
        drafts = list(result.scalars().all())
        if not drafts:
            return BulkActionResult(action=action, affected=0, message="Sin borradores en el scope activo.")

        if action == "discard":
            for d in drafts:
                d.status = "descartado"
            await self.db.commit()
            return BulkActionResult(action=action, affected=len(drafts), message=f"{len(drafts)} borrador(es) descartados.")

        if action == "export":
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["id", "client_name", "description", "cost_price", "sale_price_suggested", "status"])
            for d in drafts:
                writer.writerow([
                    str(d.id), d.client_name or "", d.description or "",
                    str(d.cost_price or ""), str(d.sale_price_suggested or ""), d.status,
                ])
            return BulkActionResult(
                action=action,
                affected=len(drafts),
                message=f"Exportados {len(drafts)} borradores.",
                export_csv=buf.getvalue(),
            )

        if action == "status" and status:
            for d in drafts:
                d.status = status
            await self.db.commit()
            return BulkActionResult(
                action=action, affected=len(drafts), message=f"Estado actualizado en {len(drafts)} borrador(es)."
            )

        if action == "assign" and assigned_user_id:
            for d in drafts:
                d.user_id = assigned_user_id
            await self.db.commit()
            return BulkActionResult(
                action=action, affected=len(drafts), message=f"Vendedor asignado en {len(drafts)} borrador(es)."
            )

        if action == "create_task":
            from app.schemas.tasks import TaskCreateRequest
            from app.models.work_enums import TaskCategory, TaskDepartment, TaskSource

            company_id = await self.scope.primary_company_id()
            created = 0
            for draft in drafts:
                if draft.task_id:
                    continue
                product_label = draft.description or "Producto"
                task = await self.tasks.create_task(
                    TaskCreateRequest(
                        title=f"Revisar cotización: {product_label[:100]}",
                        description=draft.client_name or product_label,
                        category=TaskCategory.COTIZACION.value,
                        department=TaskDepartment.VENTAS.value,
                        source=TaskSource.PRICE_INTELLIGENCE.value,
                        company_id=company_id,
                    )
                )
                draft.task_id = task.id
                created += 1
            await self.db.commit()
            return BulkActionResult(
                action=action, affected=created, message=f"{created} tarea(s) creada(s) desde borradores."
            )

        raise JAIOSException(f"Acción no soportada: {action}", code="BULK_UNSUPPORTED")
