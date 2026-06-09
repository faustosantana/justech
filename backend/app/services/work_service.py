"""Work Hub service — centro operativo diario."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.task import Task, TaskAuditLog
from app.models.user import User
from app.schemas.work import WorkActivityItem, WorkAlert, WorkDepartmentSummary, WorkHubResponse
from app.services.notification_service import NotificationService
from app.services.task_service import TaskService


class WorkService:
    def __init__(self, db, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.tasks = TaskService(db, tenant_id, user_id)
        self.notifications = NotificationService(db, tenant_id, user_id)

    async def _load_task_list(self, q) -> list:
        q = await self.tasks.apply_company_scope(q)
        result = await self.db.execute(
            q.options(
                selectinload(Task.comments),
                selectinload(Task.checklist_items),
                selectinload(Task.attachments),
            )
        )
        raw = list(result.scalars().all())
        users = await self.tasks._load_users(raw)
        return [self.tasks._to_response(t, users) for t in raw]

    async def get_hub(self) -> WorkHubResponse:
        await self.tasks.sync_due_notifications(self.user_id)
        today = date.today()
        soon = today + timedelta(days=3)

        my_q = select(Task).where(
            Task.tenant_id == self.tenant_id,
            Task.assigned_to_id == self.user_id,
            Task.status.notin_(["completada", "cancelada"]),
        )
        my_q = await self.tasks.apply_company_scope(my_q)
        my_result = await self.db.execute(
            my_q.order_by(Task.due_date.asc().nullslast()).limit(20)
        )
        my_tasks_raw = list(my_result.scalars().all())
        users = await self.tasks._load_users(my_tasks_raw)
        my_tasks = [self.tasks._to_response(t, users) for t in my_tasks_raw]

        my_pending = sum(1 for t in my_tasks_raw if t.status == "pendiente")
        my_in_progress = sum(1 for t in my_tasks_raw if t.status == "en_proceso")
        my_overdue = sum(1 for t in my_tasks_raw if t.due_date and t.due_date < today)
        my_critical = sum(1 for t in my_tasks_raw if t.priority == "critica")
        my_due_soon = sum(
            1 for t in my_tasks_raw
            if t.due_date and today <= t.due_date <= soon
        )

        created_q = select(Task).where(
            Task.tenant_id == self.tenant_id,
            Task.created_by_id == self.user_id,
            Task.status.notin_(["completada", "cancelada"]),
        ).order_by(Task.created_at.desc()).limit(10)
        tasks_created_by_me = await self._load_task_list(created_q)

        supervised_q = select(Task).where(
            Task.tenant_id == self.tenant_id,
            Task.supervisor_id == self.user_id,
            Task.status.notin_(["completada", "cancelada"]),
        ).order_by(Task.due_date.asc().nullslast()).limit(10)
        tasks_supervised_by_me = await self._load_task_list(supervised_q)

        dept_q = select(Task.department, Task.status, Task.priority, Task.due_date).where(
            Task.tenant_id == self.tenant_id,
            Task.status.notin_(["completada", "cancelada"]),
        )
        dept_q = await self.tasks.apply_company_scope(dept_q)
        dept_result = await self.db.execute(dept_q)
        dept_map: dict[str, dict[str, int]] = {}
        for dept, status, priority, due in dept_result.all():
            d = dept or "operaciones"
            if d not in dept_map:
                dept_map[d] = {"pending": 0, "overdue": 0, "critical": 0}
            if status == "pendiente":
                dept_map[d]["pending"] += 1
            if due and due < today:
                dept_map[d]["overdue"] += 1
            if priority == "critica":
                dept_map[d]["critical"] += 1

        by_department = [
            WorkDepartmentSummary(department=k, **v) for k, v in sorted(dept_map.items())
        ]

        alerts: list[WorkAlert] = []
        if my_overdue:
            alerts.append(WorkAlert(
                type="task_overdue",
                title="Tareas vencidas",
                message=f"Tienes {my_overdue} tareas vencidas",
                count=my_overdue,
                severity="critical",
                link="/tasks?status=vencida",
            ))
        if my_critical:
            alerts.append(WorkAlert(
                type="task_critical",
                title="Tareas críticas",
                message=f"{my_critical} tareas críticas requieren atención",
                count=my_critical,
                severity="critical",
                link="/tasks?priority=critica",
            ))

        crit_q = select(func.count()).select_from(Task).where(
            Task.tenant_id == self.tenant_id,
            Task.priority == "critica",
            Task.status.notin_(["completada", "cancelada"]),
        )
        crit_q = await self.tasks.apply_company_scope(crit_q)
        crit_count = await self.db.execute(crit_q)
        total_crit = crit_count.scalar_one()
        if total_crit:
            alerts.append(WorkAlert(
                type="org_critical",
                title="Críticas en la organización",
                message=f"{total_crit} tareas críticas activas",
                count=total_crit,
                severity="warning",
                link="/tasks?priority=critica",
            ))

        activity_result = await self.db.execute(
            select(TaskAuditLog)
            .where(TaskAuditLog.tenant_id == self.tenant_id)
            .order_by(TaskAuditLog.created_at.desc())
            .limit(15)
        )
        logs = list(activity_result.scalars().all())
        user_ids = {log.user_id for log in logs if log.user_id}
        user_names: dict[uuid.UUID, str] = {}
        if user_ids:
            ur = await self.db.execute(select(User.id, User.full_name).where(User.id.in_(user_ids)))
            user_names = {row[0]: row[1] for row in ur.all()}

        task_titles: dict[uuid.UUID, str] = {}
        task_ids = {log.task_id for log in logs}
        if task_ids:
            tr = await self.db.execute(select(Task.id, Task.title).where(Task.id.in_(task_ids)))
            task_titles = {row[0]: row[1] for row in tr.all()}

        ACTION_LABELS = {
            "assigned": "asignó tarea",
            "reassigned": "reasignó tarea",
            "supervisor_changed": "cambió supervisor",
            "completed": "completó tarea",
            "comment_added": "comentó",
            "checklist_updated": "actualizó checklist",
            "created": "creó tarea",
            "status_changed": "cambió estado",
        }

        recent_activity = [
            WorkActivityItem(
                action=ACTION_LABELS.get(log.action, log.action),
                task_id=str(log.task_id),
                task_title=task_titles.get(log.task_id),
                user_name=user_names.get(log.user_id) if log.user_id else None,
                created_at=log.created_at.isoformat(),
            )
            for log in logs
        ]

        notifs = await self.notifications.list_for_user(self.user_id, limit=10)
        unread = await self.notifications.unread_count(self.user_id)

        return WorkHubResponse(
            my_tasks=my_tasks,
            my_pending=my_pending,
            my_in_progress=my_in_progress,
            my_overdue=my_overdue,
            my_critical=my_critical,
            my_due_soon=my_due_soon,
            tasks_created_by_me=tasks_created_by_me,
            tasks_supervised_by_me=tasks_supervised_by_me,
            by_department=by_department,
            alerts=alerts,
            recent_activity=recent_activity,
            recent_notifications=notifs.items[:10],
            unread_notifications=unread,
        )
