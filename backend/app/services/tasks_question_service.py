"""Consultas de tareas para el Assistant."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.assistant import AssistantLink, AssistantQueryResponse
from app.services.assistant_actions import table_row
from app.services.business_answer_builder import build_business_answer, links_to_dict, not_found_summary
from app.services.business_intent_router import ParsedBusinessQuestion
from app.services.task_service import TaskService


class TasksQuestionService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.tasks = TaskService(db, tenant_id, user_id=user_id)

    async def answer(self, question: str, parsed: ParsedBusinessQuestion) -> AssistantQueryResponse:
        lowered = question.lower()

        if any(k in lowered for k in ("vencida", "vencidas")):
            return await self._overdue_tasks(question)

        if any(k in lowered for k in ("críticas", "criticas")):
            return await self._critical_tasks(question)

        if parsed.assignee_label:
            return await self._assignee_tasks(question, parsed.assignee_label)

        return AssistantQueryResponse(
            question=question,
            answer="Indica a quién consultar o el tipo de tareas (vencidas, críticas, pendientes).",
            sources=["tasks"],
            query_type="tasks_query",
        )

    async def _resolve_user(self, name: str) -> User | None:
        if name.lower() == "soporte":
            result = await self.db.execute(
                select(User).where(User.full_name.ilike("%soporte%"), User.is_active.is_(True)).limit(1)
            )
            return result.scalar_one_or_none()
        result = await self.db.execute(
            select(User).where(User.full_name.ilike(f"%{name}%"), User.is_active.is_(True)).limit(1)
        )
        return result.scalar_one_or_none()

    async def _assignee_tasks(self, question: str, assignee_name: str) -> AssistantQueryResponse:
        user = await self._resolve_user(assignee_name)
        if not user:
            return AssistantQueryResponse(
                question=question,
                answer=not_found_summary(assignee_name, "tasks", kind="tareas"),
                sources=["tasks"],
                query_type="tasks_query",
            )
        result = await self.tasks.list_tasks(assigned_to_id=user.id, limit=20)
        pending = [t for t in result.items if t.status in ("pendiente", "en_proceso")]
        if not pending:
            return AssistantQueryResponse(
                question=question,
                answer=f"No encontré tareas pendientes asignadas a {user.full_name}.",
                sources=["tasks"],
                query_type="tasks_query",
            )
        summary = f"{user.full_name} tiene {len(pending)} tareas pendientes."
        rows = [
            table_row(
                [t.title[:50], t.priority, t.status, str(t.due_date) if t.due_date else "—"],
                entity_type="task",
                entity_id=str(t.id),
            )
            for t in pending[:12]
        ]
        links = [AssistantLink(label=t.title, url=f"/tasks/{t.id}", type="task") for t in pending[:8]]
        structured = build_business_answer(
            intent="tasks_query",
            source="tasks",
            summary=summary,
            metrics=[
                {"label": "Asignado a", "value": user.full_name},
                {"label": "Pendientes", "value": str(len(pending))},
            ],
            tables=[{
                "title": "Tareas pendientes",
                "columns": ["Tarea", "Prioridad", "Estado", "Vence"],
                "rows": rows,
            }],
            links=links_to_dict(links),
        )
        return AssistantQueryResponse(
            question=question,
            answer=summary,
            sources=["tasks"],
            query_type="tasks_query",
            structured_data=structured,
            links=links,
        )

    async def _overdue_tasks(self, question: str) -> AssistantQueryResponse:
        result = await self.tasks.list_tasks(limit=50)
        overdue = [t for t in result.items if t.due_date and t.due_date < date.today() and t.status not in ("completada", "cancelada")]
        if not overdue:
            return AssistantQueryResponse(
                question=question,
                answer="No encontré tareas vencidas activas.",
                sources=["tasks"],
                query_type="tasks_query",
            )
        summary = f"Hay {len(overdue)} tareas vencidas activas."
        rows = [
            table_row(
                [
                    t.title[:50],
                    t.assigned_to_name or "—",
                    str(t.due_date),
                    t.priority,
                ],
                entity_type="task",
                entity_id=str(t.id),
            )
            for t in overdue[:12]
        ]
        links = [AssistantLink(label=t.title, url=f"/tasks/{t.id}", type="task") for t in overdue[:8]]
        structured = build_business_answer(
            intent="tasks_query",
            source="tasks",
            summary=summary,
            metrics=[{"label": "Tareas vencidas", "value": str(len(overdue))}],
            tables=[{
                "title": "Tareas vencidas",
                "columns": ["Tarea", "Asignado", "Vence", "Prioridad"],
                "rows": rows,
            }],
            links=links_to_dict(links),
        )
        return AssistantQueryResponse(
            question=question,
            answer=summary,
            sources=["tasks"],
            query_type="tasks_query",
            structured_data=structured,
            links=links,
        )

    async def _critical_tasks(self, question: str) -> AssistantQueryResponse:
        result = await self.tasks.list_tasks(priority="critica", limit=20)
        active = [t for t in result.items if t.status not in ("completada", "cancelada")]
        if not active:
            return AssistantQueryResponse(
                question=question,
                answer="No encontré tareas críticas activas.",
                sources=["tasks"],
                query_type="tasks_query",
            )
        summary = f"Hay {len(active)} tareas críticas activas."
        rows = [
            table_row(
                [t.title[:50], t.assigned_to_name or "—", t.status, str(t.due_date) if t.due_date else "—"],
                entity_type="task",
                entity_id=str(t.id),
            )
            for t in active[:12]
        ]
        links = [AssistantLink(label=t.title, url=f"/tasks/{t.id}", type="task") for t in active[:8]]
        structured = build_business_answer(
            intent="tasks_query",
            source="tasks",
            summary=summary,
            metrics=[{"label": "Críticas activas", "value": str(len(active))}],
            tables=[{
                "title": "Tareas críticas",
                "columns": ["Tarea", "Asignado", "Estado", "Vence"],
                "rows": rows,
            }],
            links=links_to_dict(links),
        )
        return AssistantQueryResponse(
            question=question,
            answer=summary,
            sources=["tasks"],
            query_type="tasks_query",
            structured_data=structured,
            links=links,
        )
