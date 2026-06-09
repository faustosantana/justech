"""Tasks Center service."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.task import Task, TaskAuditLog, TaskChecklistItem, TaskComment
from app.models.user import User
from app.models.work_enums import NotificationType, TaskStatus
from app.schemas.tasks import (
    TaskAssignmentHistoryItem,
    TaskCreateRequest,
    TaskFromEventRequest,
    TaskListResponse,
    TaskResponse,
    TaskUpdateRequest,
)
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.services.routing_service import RoutingService


class TaskService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.routing = RoutingService(db, tenant_id)
        self.notifications = NotificationService(db, tenant_id)
        self.audit = AuditService(db)

    async def _user_name(self, user_id: uuid.UUID | None) -> str | None:
        if not user_id:
            return None
        result = await self.db.execute(select(User.full_name).where(User.id == user_id))
        return result.scalar_one_or_none()

    def _to_response(
        self,
        task: Task,
        users: dict[uuid.UUID, dict[str, str | None]] | None = None,
        *,
        assignment_history: list[TaskAssignmentHistoryItem] | None = None,
        assignee_resolution_warning: str | None = None,
    ) -> TaskResponse:
        users = users or {}

        def _u(uid: uuid.UUID | None) -> dict[str, str | None]:
            return users.get(uid, {}) if uid else {}

        data = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "category": task.category,
            "department": task.department,
            "source": task.source,
            "created_by_id": task.created_by_id,
            "created_by_name": _u(task.created_by_id).get("full_name"),
            "created_by_email": _u(task.created_by_id).get("email"),
            "assigned_to_id": task.assigned_to_id,
            "assigned_to_name": _u(task.assigned_to_id).get("full_name"),
            "assigned_to_email": _u(task.assigned_to_id).get("email"),
            "supervisor_id": task.supervisor_id,
            "supervisor_name": _u(task.supervisor_id).get("full_name"),
            "supervisor_email": _u(task.supervisor_id).get("email"),
            "suggested_assignee_name": task.suggested_assignee_name,
            "assignee_resolution_warning": assignee_resolution_warning,
            "assignment_history": assignment_history or [],
            "due_date": task.due_date,
            "completed_at": task.completed_at,
            "company_id": task.company_id,
            "customer_name": task.customer_name,
            "customer_id": task.customer_id,
            "odoo_customer_id": task.odoo_customer_id,
            "odoo_invoice_id": task.odoo_invoice_id,
            "odoo_quotation_id": task.odoo_quotation_id,
            "odoo_opportunity_id": task.odoo_opportunity_id,
            "odoo_project_id": task.odoo_project_id,
            "dgcp_process_id": task.dgcp_process_id,
            "support_ticket_id": task.support_ticket_id,
            "related_email_id": task.related_email_id,
            "related_document_id": task.related_document_id,
            "amount": task.amount,
            "currency": task.currency,
            "tags": task.tags or [],
            "metadata": task.metadata_ or {},
            "comments": task.comments,
            "checklist_items": task.checklist_items,
            "attachments": task.attachments,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        }
        return TaskResponse.model_validate(data)

    async def _load_users(self, tasks: list[Task]) -> dict[uuid.UUID, dict[str, str | None]]:
        ids: set[uuid.UUID] = set()
        for t in tasks:
            for uid in (t.created_by_id, t.assigned_to_id, t.supervisor_id):
                if uid:
                    ids.add(uid)
        if not ids:
            return {}
        result = await self.db.execute(
            select(User.id, User.full_name, User.email).where(User.id.in_(ids))
        )
        return {
            row[0]: {"full_name": row[1], "email": row[2]}
            for row in result.all()
        }

    async def _load_assignment_history(self, task_id: uuid.UUID) -> list[TaskAssignmentHistoryItem]:
        result = await self.db.execute(
            select(TaskAuditLog)
            .where(
                TaskAuditLog.task_id == task_id,
                TaskAuditLog.tenant_id == self.tenant_id,
                TaskAuditLog.action.in_(
                    ["assigned", "reassigned", "supervisor_changed", "completed"]
                ),
            )
            .order_by(TaskAuditLog.created_at.desc())
            .limit(20)
        )
        logs = list(result.scalars().all())
        user_ids = {log.user_id for log in logs if log.user_id}
        names: dict[uuid.UUID, str] = {}
        if user_ids:
            ur = await self.db.execute(select(User.id, User.full_name).where(User.id.in_(user_ids)))
            names = {row[0]: row[1] for row in ur.all()}
        return [
            TaskAssignmentHistoryItem(
                action=log.action,
                user_name=names.get(log.user_id) if log.user_id else None,
                details=log.details or {},
                created_at=log.created_at,
            )
            for log in logs
        ]

    async def _task_audit(self, task_id: uuid.UUID, action: str, details: dict | None = None) -> None:
        entry = TaskAuditLog(
            tenant_id=self.tenant_id,
            task_id=task_id,
            user_id=self.user_id,
            action=action,
            details=details or {},
        )
        self.db.add(entry)
        await self.audit.log(
            action=f"tasks.{action}",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="task",
            resource_id=task_id,
            details=details,
        )

    async def apply_company_scope(self, q):
        if not self.user_id:
            return q
        from app.services.company_scope_filter import CompanyScopeFilter

        clause = await CompanyScopeFilter(
            self.db, self.tenant_id, self.user_id
        ).task_company_clause(Task.company_id)
        if clause is not None:
            q = q.where(clause)
        return q

    async def list_tasks(
        self,
        *,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        department: str | None = None,
        assigned_to_id: uuid.UUID | None = None,
        search: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> TaskListResponse:
        q = select(Task).where(Task.tenant_id == self.tenant_id)
        if self.user_id:
            from app.services.company_scope_filter import CompanyScopeFilter

            clause = await CompanyScopeFilter(
                self.db, self.tenant_id, self.user_id
            ).task_company_clause(Task.company_id)
            if clause is not None:
                q = q.where(clause)
        if status:
            q = q.where(Task.status == status)
        if priority:
            q = q.where(Task.priority == priority)
        if category:
            q = q.where(Task.category == category)
        if department:
            q = q.where(Task.department == department)
        if assigned_to_id:
            q = q.where(Task.assigned_to_id == assigned_to_id)
        if search:
            pattern = f"%{search}%"
            q = q.where(
                or_(
                    Task.title.ilike(pattern),
                    Task.description.ilike(pattern),
                    Task.customer_name.ilike(pattern),
                )
            )

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        q = (
            q.options(
                selectinload(Task.comments),
                selectinload(Task.checklist_items),
                selectinload(Task.attachments),
            )
            .order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(q)
        tasks = list(result.scalars().all())
        users = await self._load_users(tasks)
        return TaskListResponse(
            items=[self._to_response(t, users) for t in tasks],
            total=total,
        )

    async def get_task(self, task_id: uuid.UUID) -> TaskResponse | None:
        result = await self.db.execute(
            select(Task)
            .options(
                selectinload(Task.comments),
                selectinload(Task.checklist_items),
                selectinload(Task.attachments),
            )
            .where(Task.id == task_id, Task.tenant_id == self.tenant_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            return None
        if self.user_id and task.company_id is not None:
            from app.services.company_scope_filter import CompanyScopeFilter

            await CompanyScopeFilter(
                self.db, self.tenant_id, self.user_id
            ).assert_company_id_allowed(task.company_id)
        users = await self._load_users([task])
        history = await self._load_assignment_history(task_id)
        warning = None
        if task.suggested_assignee_name and not task.assigned_to_id:
            warning = (
                f"No se encontró usuario JAIOS para «{task.suggested_assignee_name}». "
                "Asigne manualmente."
            )
        return self._to_response(
            task,
            users,
            assignment_history=history,
            assignee_resolution_warning=warning,
        )

    async def create_task(self, payload: TaskCreateRequest) -> TaskResponse:
        company_id = payload.company_id
        if self.user_id and not company_id:
            from app.services.company_scope_filter import CompanyScopeFilter

            company_id = await CompanyScopeFilter(
                self.db, self.tenant_id, self.user_id
            ).primary_company_id()
        task = Task(
            tenant_id=self.tenant_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            priority=payload.priority,
            category=payload.category,
            department=payload.department,
            source=payload.source,
            created_by_id=self.user_id,
            assigned_to_id=payload.assigned_to_id,
            suggested_assignee_name=payload.suggested_assignee_name,
            supervisor_id=payload.supervisor_id,
            due_date=payload.due_date,
            company_id=company_id,
            customer_name=payload.customer_name,
            customer_id=payload.customer_id,
            odoo_customer_id=payload.odoo_customer_id,
            odoo_invoice_id=payload.odoo_invoice_id,
            odoo_quotation_id=payload.odoo_quotation_id,
            odoo_opportunity_id=payload.odoo_opportunity_id,
            odoo_project_id=payload.odoo_project_id,
            dgcp_process_id=payload.dgcp_process_id,
            support_ticket_id=payload.support_ticket_id,
            related_email_id=payload.related_email_id,
            related_document_id=payload.related_document_id,
            amount=payload.amount,
            currency=payload.currency,
            tags=payload.tags,
            metadata_=payload.metadata,
        )
        self.db.add(task)
        await self.db.flush()

        for i, text in enumerate(payload.checklist):
            self.db.add(TaskChecklistItem(task_id=task.id, text=text, sort_order=i))

        await self._task_audit(task.id, "created", {"title": task.title})
        if task.assigned_to_id:
            await self._task_audit(
                task.id,
                "assigned",
                {
                    "assigned_to_id": str(task.assigned_to_id),
                    "assigned_to_name": await self._user_name(task.assigned_to_id),
                },
            )
            await self._notify_assigned(task, is_reassign=False)
        if task.supervisor_id:
            await self._task_audit(
                task.id,
                "supervisor_changed",
                {
                    "supervisor_id": str(task.supervisor_id),
                    "supervisor_name": await self._user_name(task.supervisor_id),
                },
            )

        await self.db.flush()
        return (await self.get_task(task.id))  # type: ignore[return-value]

    async def create_from_event(self, payload: TaskFromEventRequest) -> TaskResponse:
        routing_data = None
        checklist: list[str] = []
        if payload.apply_routing:
            routing_data = await self.routing.preview(
                event_type=payload.event_type,
                title=payload.title,
                description=payload.description or "",
                customer_name=payload.customer_name,
                amount=float(payload.amount) if payload.amount else None,
                metadata=payload.metadata,
            )
            checklist = routing_data.checklist
            assignee_id = await self.routing.resolve_assignee_id(routing_data.suggested_assignee_name)
            supervisor_id = await self.routing.resolve_supervisor_id(
                routing_data.suggested_assignee_name
            )
            create = TaskCreateRequest(
                title=payload.title,
                description=payload.description,
                category=routing_data.category,
                department=routing_data.department,
                priority=routing_data.priority,
                source=payload.source,
                assigned_to_id=assignee_id,
                supervisor_id=supervisor_id,
                suggested_assignee_name=routing_data.suggested_assignee_name,
                due_date=routing_data.due_date,
                customer_name=payload.customer_name,
                amount=payload.amount,
                currency=payload.currency,
                odoo_customer_id=payload.odoo_customer_id,
                odoo_invoice_id=payload.odoo_invoice_id,
                odoo_quotation_id=payload.odoo_quotation_id,
                odoo_opportunity_id=payload.odoo_opportunity_id,
                odoo_project_id=payload.odoo_project_id,
                dgcp_process_id=payload.dgcp_process_id,
                metadata={
                    **payload.metadata,
                    "routing_rule": routing_data.matched_rule,
                    "related_entity_type": payload.related_entity_type,
                    "related_entity_id": payload.related_entity_id,
                },
                checklist=checklist,
            )
        else:
            create = TaskCreateRequest(
                title=payload.title,
                description=payload.description,
                source=payload.source,
                customer_name=payload.customer_name,
                amount=payload.amount,
                currency=payload.currency,
                odoo_customer_id=payload.odoo_customer_id,
                odoo_invoice_id=payload.odoo_invoice_id,
                odoo_quotation_id=payload.odoo_quotation_id,
                odoo_opportunity_id=payload.odoo_opportunity_id,
                odoo_project_id=payload.odoo_project_id,
                dgcp_process_id=payload.dgcp_process_id,
                metadata=payload.metadata,
            )

        return await self.create_task(create)

    async def update_task(self, task_id: uuid.UUID, payload: TaskUpdateRequest) -> TaskResponse | None:
        result = await self.db.execute(
            select(Task).where(Task.id == task_id, Task.tenant_id == self.tenant_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            return None

        old_status = task.status
        old_assignee = task.assigned_to_id
        old_supervisor = task.supervisor_id
        updates = payload.model_dump(exclude_unset=True)
        for key, value in updates.items():
            if key == "metadata":
                task.metadata_ = {**(task.metadata_ or {}), **value}
            else:
                setattr(task, key, value)

        if payload.status == TaskStatus.COMPLETADA.value and not task.completed_at:
            task.completed_at = datetime.now(timezone.utc)

        non_assignment_updates = {
            k: v for k, v in updates.items()
            if k not in ("assigned_to_id", "supervisor_id", "suggested_assignee_name")
        }
        if non_assignment_updates:
            await self._task_audit(task_id, "updated", non_assignment_updates)

        if old_assignee != task.assigned_to_id:
            action = "reassigned" if old_assignee else "assigned"
            await self._task_audit(
                task_id,
                action,
                {
                    "from_id": str(old_assignee) if old_assignee else None,
                    "to_id": str(task.assigned_to_id) if task.assigned_to_id else None,
                    "to_name": await self._user_name(task.assigned_to_id),
                },
            )
            if task.assigned_to_id:
                await self._notify_assigned(task, is_reassign=old_assignee is not None)

        if old_supervisor != task.supervisor_id:
            await self._task_audit(
                task_id,
                "supervisor_changed",
                {
                    "from_id": str(old_supervisor) if old_supervisor else None,
                    "to_id": str(task.supervisor_id) if task.supervisor_id else None,
                    "to_name": await self._user_name(task.supervisor_id),
                },
            )

        if old_status != task.status:
            await self._task_audit(task_id, "status_changed", {"from": old_status, "to": task.status})
            if task.status == TaskStatus.COMPLETADA.value:
                await self._task_audit(task_id, "completed", {"title": task.title})
                await self._notify_completed(task)

        await self.db.flush()
        return await self.get_task(task_id)

    async def delete_task(self, task_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(Task).where(Task.id == task_id, Task.tenant_id == self.tenant_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            return False
        await self._task_audit(task_id, "deleted", {"title": task.title})
        await self.db.delete(task)
        return True

    async def add_comment(self, task_id: uuid.UUID, comment: str) -> TaskResponse | None:
        result = await self.db.execute(
            select(Task).where(Task.id == task_id, Task.tenant_id == self.tenant_id)
        )
        if not result.scalar_one_or_none():
            return None
        user_name = await self._user_name(self.user_id)
        self.db.add(
            TaskComment(
                task_id=task_id,
                user_id=self.user_id,
                user_name=user_name,
                comment=comment,
            )
        )
        await self._task_audit(task_id, "comment_added", {"comment": comment[:200]})
        if task := (await self.db.execute(select(Task).where(Task.id == task_id))).scalar_one():
            if task.assigned_to_id and task.assigned_to_id != self.user_id:
                await self.notifications.create(
                    user_id=task.assigned_to_id,
                    title="Nuevo comentario en tarea",
                    message=comment[:200],
                    type=NotificationType.TASK_COMMENTED.value,
                    related_task_id=task_id,
                )
        await self.db.flush()
        return await self.get_task(task_id)

    async def add_checklist_item(self, task_id: uuid.UUID, text: str) -> TaskResponse | None:
        result = await self.db.execute(
            select(Task).where(Task.id == task_id, Task.tenant_id == self.tenant_id)
        )
        if not result.scalar_one_or_none():
            return None
        count = await self.db.execute(
            select(func.count()).select_from(TaskChecklistItem).where(TaskChecklistItem.task_id == task_id)
        )
        self.db.add(
            TaskChecklistItem(task_id=task_id, text=text, sort_order=count.scalar_one())
        )
        await self._task_audit(task_id, "checklist_added", {"text": text})
        await self.db.flush()
        return await self.get_task(task_id)

    async def update_checklist_item(
        self, task_id: uuid.UUID, item_id: uuid.UUID, completed: bool
    ) -> TaskResponse | None:
        result = await self.db.execute(
            select(TaskChecklistItem).where(
                TaskChecklistItem.id == item_id,
                TaskChecklistItem.task_id == task_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            return None
        item.completed = completed
        if completed:
            item.completed_by_id = self.user_id
            item.completed_by_name = await self._user_name(self.user_id)
            item.completed_at = datetime.now(timezone.utc)
        else:
            item.completed_by_id = None
            item.completed_by_name = None
            item.completed_at = None
        await self._task_audit(task_id, "checklist_updated", {"item_id": str(item_id), "completed": completed})
        await self.db.flush()
        return await self.get_task(task_id)

    async def _notify_assigned(self, task: Task, *, is_reassign: bool) -> None:
        if not task.assigned_to_id:
            return
        ntype = (
            NotificationType.TASK_REASSIGNED.value
            if is_reassign
            else NotificationType.TASK_ASSIGNED.value
        )
        title = "Tarea reasignada" if is_reassign else "Tarea asignada"
        await self.notifications.create(
            user_id=task.assigned_to_id,
            title=title,
            message=f"{'Se te reasignó' if is_reassign else 'Se te asignó'}: {task.title}",
            type=ntype,
            severity="info" if task.priority != "critica" else "critical",
            related_task_id=task.id,
        )

    async def _notify_completed(self, task: Task) -> None:
        notify_ids: set[uuid.UUID] = set()
        if task.created_by_id:
            notify_ids.add(task.created_by_id)
        if task.supervisor_id:
            notify_ids.add(task.supervisor_id)
        notify_ids.discard(self.user_id)
        for uid in notify_ids:
            await self.notifications.create(
                user_id=uid,
                title="Tarea completada",
                message=f"Completada: {task.title}",
                type=NotificationType.TASK_COMPLETED.value,
                severity="info",
                related_task_id=task.id,
            )

    async def sync_due_notifications(self, user_id: uuid.UUID) -> None:
        """Alertas de vencimiento para tareas asignadas al usuario."""
        from datetime import date, timedelta

        today = date.today()
        soon = today + timedelta(days=3)
        result = await self.db.execute(
            select(Task).where(
                Task.tenant_id == self.tenant_id,
                Task.assigned_to_id == user_id,
                Task.status.notin_(["completada", "cancelada"]),
            )
        )
        for task in result.scalars().all():
            meta = task.metadata_ or {}
            if task.due_date and task.due_date < today and not meta.get("notified_overdue"):
                await self.notifications.create(
                    user_id=user_id,
                    title="Tarea vencida",
                    message=f"Venció: {task.title}",
                    type=NotificationType.TASK_OVERDUE.value,
                    severity="critical",
                    related_task_id=task.id,
                )
                task.metadata_ = {**meta, "notified_overdue": True}
            elif (
                task.due_date
                and today <= task.due_date <= soon
                and not meta.get("notified_due_soon")
            ):
                await self.notifications.create(
                    user_id=user_id,
                    title="Tarea por vencer",
                    message=f"Vence pronto: {task.title} ({task.due_date})",
                    type=NotificationType.TASK_DUE_SOON.value,
                    severity="warning",
                    related_task_id=task.id,
                )
                task.metadata_ = {**meta, "notified_due_soon": True}
        await self.db.flush()
