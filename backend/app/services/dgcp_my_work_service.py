"""Centro operativo Mis Licitaciones — checklist / pendientes / alertas."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.dgcp_preparation import (
    DGCPChecklistTemplate,
    DGCPChecklistTemplateItem,
    DGCPPrepAlertLog,
    DGCPPreparationTask,
)
from app.models.notification import Notification
from app.models.user import User
from app.schemas.dgcp_preparation import (
    ApplyTemplateResponse,
    ChecklistProgress,
    HoyItem,
    HoyResponse,
    MyLicitacionRow,
    MyLicitacionesResponse,
    MyWorkSummary,
    PrepChecklistResponse,
    PrepTaskCreate,
    PrepTaskOut,
    PrepTaskUpdate,
    TemplateCreate,
    TemplateItemIn,
    TemplateOut,
)
from app.services.dgcp_funnel import STATUS_LABELS_ES as STATUS_LABELS
from app.services.notification_service import NotificationService
from app.models.work_enums import NotificationType

PREP_STATUSES = frozenset(
    {"interested", "preparing", "to_bid", "pending_documents", "ready_to_submit", "submitted"}
)
OPEN_TASK_STATUSES = frozenset({"pending", "in_progress"})
DEFAULT_TEMPLATE_ITEMS: list[tuple[str, str, str, int | None]] = [
    ("revisar_pliego", "Revisar pliego", "high", None),
    ("confirmar_participacion", "Confirmar participación", "high", None),
    ("revisar_productos", "Revisar productos solicitados", "medium", None),
    ("cotizacion_proveedor", "Solicitar cotización proveedor", "high", -72),
    ("carta_fabricante", "Carta de fabricante", "high", -48),
    ("garantia_seriedad", "Garantía de seriedad", "high", -36),
    ("registro_mercantil", "Registro mercantil", "medium", -48),
    ("oferta_economica", "Preparar oferta económica", "high", -24),
    ("revision_final", "Revisión final", "high", -12),
    ("subir_oferta", "Subir oferta", "high", -2),
]


def traffic_light(due: datetime | date | None, *, now: datetime | None = None) -> tuple[str, float | None]:
    if due is None:
        return "none", None
    now = now or datetime.now(UTC)
    if isinstance(due, date) and not isinstance(due, datetime):
        due_dt = datetime(due.year, due.month, due.day, 23, 59, 59, tzinfo=UTC)
    else:
        due_dt = due if due.tzinfo else due.replace(tzinfo=UTC)
    hours = (due_dt - now).total_seconds() / 3600.0
    if hours < 0:
        return "black", hours
    if hours < 24:
        return "red", hours
    if hours < 48:
        return "orange", hours
    if hours <= 5 * 24:
        return "yellow", hours
    return "green", hours


def _deadline_as_dt(d: date | datetime | None) -> datetime | None:
    if d is None:
        return None
    if isinstance(d, datetime):
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    return datetime(d.year, d.month, d.day, 17, 0, 0, tzinfo=UTC)


class DGCPMyWorkService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    # ── helpers ──────────────────────────────────────────────

    async def _user_names(self, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not ids:
            return {}
        rows = (
            await self.db.execute(select(User).where(User.id.in_(list(ids))))
        ).scalars().all()
        out: dict[uuid.UUID, str] = {}
        for u in rows:
            name = (getattr(u, "full_name", None) or getattr(u, "name", None) or u.email or str(u.id)).strip()
            out[u.id] = name
        return out

    def _responsible_id(self, opp: DGCPOpportunity) -> uuid.UUID | None:
        info = opp.full_info or {}
        raw = info.get("responsible_user_id") or info.get("assignee_user_id")
        if not raw:
            return None
        try:
            return uuid.UUID(str(raw))
        except ValueError:
            return None

    def _task_out(self, t: DGCPPreparationTask, names: dict[uuid.UUID, str]) -> PrepTaskOut:
        light, hours = traffic_light(t.due_at)
        return PrepTaskOut(
            id=t.id,
            opportunity_id=t.opportunity_id,
            title=t.title,
            description=t.description,
            status=t.status,
            priority=t.priority,
            assigned_user_id=t.assigned_user_id,
            assigned_user_name=names.get(t.assigned_user_id) if t.assigned_user_id else None,
            due_at=t.due_at,
            template_item_key=t.template_item_key,
            created_by_id=t.created_by_id,
            completed_by_id=t.completed_by_id,
            completed_at=t.completed_at,
            created_at=t.created_at,
            updated_at=t.updated_at,
            traffic_light=light,  # type: ignore[arg-type]
            hours_remaining=round(hours, 1) if hours is not None else None,
        )

    def _progress(self, tasks: list[DGCPPreparationTask]) -> ChecklistProgress:
        applicable = [t for t in tasks if t.status != "not_applicable"]
        completed = [t for t in applicable if t.status == "completed"]
        pct = (len(completed) / len(applicable) * 100.0) if applicable else 0.0
        return ChecklistProgress(completed=len(completed), applicable=len(applicable), pct=round(pct, 1))

    def _next_pending(self, tasks: list[DGCPPreparationTask]) -> DGCPPreparationTask | None:
        open_tasks = [t for t in tasks if t.status in OPEN_TASK_STATUSES]
        if not open_tasks:
            return None
        with_due = [t for t in open_tasks if t.due_at]
        without = [t for t in open_tasks if not t.due_at]
        with_due.sort(key=lambda t: t.due_at or datetime.max.replace(tzinfo=UTC))
        return with_due[0] if with_due else (without[0] if without else None)

    # ── templates ────────────────────────────────────────────

    async def ensure_default_template(self) -> DGCPChecklistTemplate:
        existing = (
            await self.db.execute(
                select(DGCPChecklistTemplate).where(
                    DGCPChecklistTemplate.tenant_id == self.tenant_id,
                    DGCPChecklistTemplate.is_default.is_(True),
                )
            )
        ).scalar_one_or_none()
        if existing:
            return existing
        tpl = DGCPChecklistTemplate(
            tenant_id=self.tenant_id,
            name="Plantilla general",
            description="Checklist operativo de preparación",
            is_default=True,
            created_by_id=self.user_id,
        )
        self.db.add(tpl)
        await self.db.flush()
        for i, (key, title, prio, offset) in enumerate(DEFAULT_TEMPLATE_ITEMS):
            self.db.add(
                DGCPChecklistTemplateItem(
                    tenant_id=self.tenant_id,
                    template_id=tpl.id,
                    item_key=key,
                    title=title,
                    priority=prio,
                    sort_order=i,
                    default_offset_hours=offset,
                )
            )
        await self.db.flush()
        return tpl

    async def list_templates(self) -> list[TemplateOut]:
        await self.ensure_default_template()
        tpls = (
            await self.db.execute(
                select(DGCPChecklistTemplate)
                .where(
                    DGCPChecklistTemplate.tenant_id == self.tenant_id,
                    DGCPChecklistTemplate.is_active.is_(True),
                )
                .order_by(DGCPChecklistTemplate.is_default.desc(), DGCPChecklistTemplate.name)
            )
        ).scalars().all()
        out: list[TemplateOut] = []
        for tpl in tpls:
            items = (
                await self.db.execute(
                    select(DGCPChecklistTemplateItem)
                    .where(DGCPChecklistTemplateItem.template_id == tpl.id)
                    .order_by(DGCPChecklistTemplateItem.sort_order)
                )
            ).scalars().all()
            out.append(
                TemplateOut(
                    id=tpl.id,
                    name=tpl.name,
                    description=tpl.description,
                    is_default=tpl.is_default,
                    is_active=tpl.is_active,
                    items=[
                        TemplateItemIn(
                            item_key=i.item_key,
                            title=i.title,
                            description=i.description,
                            priority=i.priority,  # type: ignore[arg-type]
                            sort_order=i.sort_order,
                            default_offset_hours=i.default_offset_hours,
                        )
                        for i in items
                    ],
                )
            )
        return out

    async def create_template(self, data: TemplateCreate) -> TemplateOut:
        if data.is_default:
            rows = (
                await self.db.execute(
                    select(DGCPChecklistTemplate).where(
                        DGCPChecklistTemplate.tenant_id == self.tenant_id,
                        DGCPChecklistTemplate.is_default.is_(True),
                    )
                )
            ).scalars().all()
            for r in rows:
                r.is_default = False
        tpl = DGCPChecklistTemplate(
            tenant_id=self.tenant_id,
            name=data.name,
            description=data.description,
            is_default=data.is_default,
            created_by_id=self.user_id,
        )
        self.db.add(tpl)
        await self.db.flush()
        for it in data.items:
            self.db.add(
                DGCPChecklistTemplateItem(
                    tenant_id=self.tenant_id,
                    template_id=tpl.id,
                    item_key=it.item_key,
                    title=it.title,
                    description=it.description,
                    priority=it.priority,
                    sort_order=it.sort_order,
                    default_offset_hours=it.default_offset_hours,
                )
            )
        await self.db.flush()
        return (await self.list_templates())[0] if False else next(
            t for t in await self.list_templates() if t.id == tpl.id
        )

    # ── tasks CRUD ───────────────────────────────────────────

    async def list_tasks_for_opportunity(self, opportunity_id: uuid.UUID) -> list[DGCPPreparationTask]:
        return list(
            (
                await self.db.execute(
                    select(DGCPPreparationTask)
                    .where(
                        DGCPPreparationTask.tenant_id == self.tenant_id,
                        DGCPPreparationTask.opportunity_id == opportunity_id,
                    )
                    .order_by(
                        DGCPPreparationTask.due_at.asc().nullslast(),
                        DGCPPreparationTask.created_at.asc(),
                    )
                )
            ).scalars().all()
        )

    async def get_checklist(self, opportunity_id: uuid.UUID) -> PrepChecklistResponse:
        opp = await self._get_opp(opportunity_id)
        tasks = await self.list_tasks_for_opportunity(opportunity_id)
        ids = {t.assigned_user_id for t in tasks if t.assigned_user_id}
        rid = self._responsible_id(opp)
        if rid:
            ids.add(rid)
        names = await self._user_names(ids)
        next_t = self._next_pending(tasks)
        open_for_resp = 0
        if rid:
            open_for_resp = sum(
                1 for t in tasks if t.assigned_user_id == rid and t.status in OPEN_TASK_STATUSES
            )
        return PrepChecklistResponse(
            opportunity_id=opportunity_id,
            process_deadline=_deadline_as_dt(opp.deadline),
            responsible_user_id=rid,
            responsible_name=names.get(rid) if rid else (opp.full_info or {}).get("responsible_name"),
            progress=self._progress(tasks),
            next_pending=self._task_out(next_t, names) if next_t else None,
            items=[self._task_out(t, names) for t in tasks],
            open_tasks_assigned_to_responsible=open_for_resp,
        )

    async def set_responsible(
        self,
        opportunity_id: uuid.UUID,
        *,
        responsible_user_id: uuid.UUID | None,
        reassign_open_tasks: bool = False,
    ):
        from app.schemas.dgcp_preparation import SetResponsibleResponse

        opp = await self._get_opp(opportunity_id)
        previous = self._responsible_id(opp)
        info = dict(opp.full_info or {})
        if responsible_user_id:
            info["responsible_user_id"] = str(responsible_user_id)
            names = await self._user_names({responsible_user_id})
            info["responsible_name"] = names.get(responsible_user_id)
        else:
            info.pop("responsible_user_id", None)
            info.pop("responsible_name", None)
        opp.full_info = info

        open_prev = 0
        reassigned = 0
        notification_sent = False
        now = datetime.now(UTC)
        tasks = await self.list_tasks_for_opportunity(opportunity_id)
        if previous:
            open_prev = sum(
                1 for t in tasks if t.assigned_user_id == previous and t.status in OPEN_TASK_STATUSES
            )

        if reassign_open_tasks and responsible_user_id and previous and previous != responsible_user_id:
            for t in tasks:
                if t.status not in OPEN_TASK_STATUSES:
                    continue
                if t.assigned_user_id != previous:
                    continue
                prev_assignee = t.assigned_user_id
                t.assigned_user_id = responsible_user_id
                meta = dict(t.meta or {})
                history = list(meta.get("reassignment_history") or [])
                history.append(
                    {
                        "previous_assigned_user_id": str(prev_assignee) if prev_assignee else None,
                        "new_assigned_user_id": str(responsible_user_id),
                        "reassigned_by": str(self.user_id),
                        "reassigned_at": now.isoformat(),
                        "reason": "responsible_change",
                    }
                )
                meta["reassignment_history"] = history
                meta["previous_assigned_user_id"] = str(prev_assignee) if prev_assignee else None
                meta["new_assigned_user_id"] = str(responsible_user_id)
                meta["reassigned_by"] = str(self.user_id)
                meta["reassigned_at"] = now.isoformat()
                t.meta = meta
                reassigned += 1

            if reassigned > 0:
                notification_sent = await self._notify_reassignment(
                    user_id=responsible_user_id,
                    opportunity_id=opportunity_id,
                    opportunity_code=opp.code,
                    count=reassigned,
                )

        await self.db.flush()
        checklist = await self.get_checklist(opportunity_id)
        return SetResponsibleResponse(
            checklist=checklist,
            previous_responsible_user_id=previous,
            new_responsible_user_id=responsible_user_id,
            open_tasks_previous_responsible=open_prev,
            reassigned_count=reassigned,
            reassign_open_tasks=reassign_open_tasks,
            notification_sent=notification_sent,
        )

    async def _notify_reassignment(
        self,
        *,
        user_id: uuid.UUID,
        opportunity_id: uuid.UUID,
        opportunity_code: str,
        count: int,
    ) -> bool:
        """Una sola notificación interna al nuevo responsable (con dedup)."""
        alert_type = "prep_reassigned_batch"
        deadline_key = datetime.now(UTC).strftime("%Y%m%d%H")
        dedup = f"{user_id}:{opportunity_id}:-:{alert_type}:{deadline_key}:{count}"
        exists = (
            await self.db.execute(
                select(DGCPPrepAlertLog).where(
                    DGCPPrepAlertLog.tenant_id == self.tenant_id,
                    DGCPPrepAlertLog.dedup_key == dedup,
                )
            )
        ).scalar_one_or_none()
        if exists:
            return False
        notif = NotificationService(self.db, self.tenant_id)
        n = await notif.create(
            user_id=user_id,
            title=f"Se te asignaron {count} pendientes de {opportunity_code}"[:255],
            message=f"Reasignación por cambio de responsable · {opportunity_code}",
            type=NotificationType.DGCP_DEADLINE.value,
            severity="info",
            related_entity_type="dgcp_opportunity",
            related_entity_id=str(opportunity_id),
        )
        self.db.add(
            DGCPPrepAlertLog(
                tenant_id=self.tenant_id,
                dedup_key=dedup,
                user_id=user_id,
                opportunity_id=opportunity_id,
                task_id=None,
                alert_type=alert_type,
                deadline_key=deadline_key,
                notification_id=getattr(n, "id", None),
            )
        )
        return True

    async def create_task(self, opportunity_id: uuid.UUID, data: PrepTaskCreate) -> PrepTaskOut:
        await self._get_opp(opportunity_id)
        task = DGCPPreparationTask(
            tenant_id=self.tenant_id,
            opportunity_id=opportunity_id,
            title=data.title.strip(),
            description=data.description,
            priority=data.priority,
            assigned_user_id=data.assigned_user_id or self.user_id,
            due_at=data.due_at,
            created_by_id=self.user_id,
        )
        self.db.add(task)
        await self.db.flush()
        names = await self._user_names({task.assigned_user_id} if task.assigned_user_id else set())
        return self._task_out(task, names)

    async def toggle_complete(self, task_id: uuid.UUID) -> PrepTaskOut:
        task = await self._get_task(task_id)
        if task.status == "completed":
            task.status = "pending"
            task.completed_at = None
            task.completed_by_id = None
        else:
            task.status = "completed"
            task.completed_at = datetime.now(UTC)
            task.completed_by_id = self.user_id
        await self.db.flush()
        await self.db.refresh(task)
        names: dict[uuid.UUID, str] = {}
        if task.assigned_user_id:
            names = await self._user_names({task.assigned_user_id})
        return self._task_out(task, names)

    async def update_task(self, task_id: uuid.UUID, data: PrepTaskUpdate) -> PrepTaskOut:
        task = await self._get_task(task_id)
        if data.title is not None:
            task.title = data.title.strip()
        if data.description is not None:
            task.description = data.description
        if data.priority is not None:
            task.priority = data.priority
        if "assigned_user_id" in data.model_fields_set:
            task.assigned_user_id = data.assigned_user_id
        if "due_at" in data.model_fields_set:
            task.due_at = data.due_at
        if data.status is not None:
            task.status = data.status
            if data.status == "completed":
                task.completed_at = datetime.now(UTC)
                task.completed_by_id = self.user_id
            elif data.status in OPEN_TASK_STATUSES or data.status == "not_applicable":
                task.completed_at = None
                task.completed_by_id = None
        await self.db.flush()
        await self.db.refresh(task)
        names: dict[uuid.UUID, str] = {}
        if task.assigned_user_id:
            names = await self._user_names({task.assigned_user_id})
        return self._task_out(task, names)

    async def apply_template(
        self,
        opportunity_id: uuid.UUID,
        *,
        template_id: uuid.UUID | None = None,
        assign_to_responsible: bool = True,
    ) -> ApplyTemplateResponse:
        opp = await self._get_opp(opportunity_id)
        if template_id:
            tpl = (
                await self.db.execute(
                    select(DGCPChecklistTemplate).where(
                        DGCPChecklistTemplate.tenant_id == self.tenant_id,
                        DGCPChecklistTemplate.id == template_id,
                    )
                )
            ).scalar_one_or_none()
            if not tpl:
                raise ValueError("Plantilla no encontrada")
        else:
            tpl = await self.ensure_default_template()

        items = (
            await self.db.execute(
                select(DGCPChecklistTemplateItem)
                .where(DGCPChecklistTemplateItem.template_id == tpl.id)
                .order_by(DGCPChecklistTemplateItem.sort_order)
            )
        ).scalars().all()
        existing = await self.list_tasks_for_opportunity(opportunity_id)
        existing_keys = {t.template_item_key for t in existing if t.template_item_key}

        assignee = self._responsible_id(opp) if assign_to_responsible else self.user_id
        process_dl = _deadline_as_dt(opp.deadline)
        created = 0
        skipped = 0
        for it in items:
            if it.item_key in existing_keys:
                skipped += 1
                continue
            due_at = None
            if process_dl and it.default_offset_hours is not None:
                due_at = process_dl + timedelta(hours=it.default_offset_hours)
            self.db.add(
                DGCPPreparationTask(
                    tenant_id=self.tenant_id,
                    opportunity_id=opportunity_id,
                    title=it.title,
                    description=it.description,
                    priority=it.priority,
                    assigned_user_id=assignee or self.user_id,
                    due_at=due_at,
                    template_id=tpl.id,
                    template_item_key=it.item_key,
                    created_by_id=self.user_id,
                )
            )
            created += 1
        await self.db.flush()
        checklist = await self.get_checklist(opportunity_id)
        return ApplyTemplateResponse(
            opportunity_id=opportunity_id,
            template_id=tpl.id,
            created=created,
            skipped_duplicates=skipped,
            items=checklist.items,
        )

    # ── Mis Licitaciones / Hoy / Mis Pendientes ──────────────

    async def list_my_licitations(
        self,
        *,
        scope: str = "mine",
        company: str | None = None,
        q: str | None = None,
        limit: int = 100,
    ) -> MyLicitacionesResponse:
        now = datetime.now(UTC)
        # Candidate opps: prep statuses OR have prep tasks
        task_opp_ids = set(
            (
                await self.db.execute(
                    select(DGCPPreparationTask.opportunity_id).where(
                        DGCPPreparationTask.tenant_id == self.tenant_id
                    ).distinct()
                )
            ).scalars().all()
        )

        q_opp = select(DGCPOpportunity).where(DGCPOpportunity.tenant_id == self.tenant_id)
        if company:
            q_opp = q_opp.where(DGCPOpportunity.company == company)
        opps = list((await self.db.execute(q_opp.order_by(DGCPOpportunity.deadline.asc()))).scalars().all())

        # Load all tasks for candidate set
        all_tasks = list(
            (
                await self.db.execute(
                    select(DGCPPreparationTask).where(DGCPPreparationTask.tenant_id == self.tenant_id)
                )
            ).scalars().all()
        )
        tasks_by_opp: dict[uuid.UUID, list[DGCPPreparationTask]] = {}
        for t in all_tasks:
            tasks_by_opp.setdefault(t.opportunity_id, []).append(t)

        name_ids: set[uuid.UUID] = set()
        for opp in opps:
            rid = self._responsible_id(opp)
            if rid:
                name_ids.add(rid)
        for t in all_tasks:
            if t.assigned_user_id:
                name_ids.add(t.assigned_user_id)
        names = await self._user_names(name_ids)

        rows: list[MyLicitacionRow] = []
        for opp in opps:
            rid = self._responsible_id(opp)
            tasks = tasks_by_opp.get(opp.id, [])
            mine_task = any(t.assigned_user_id == self.user_id and t.status in OPEN_TASK_STATUSES for t in tasks)
            is_responsible = rid == self.user_id
            in_prep = opp.status in PREP_STATUSES
            unassigned = rid is None and in_prep

            include = False
            if scope == "all":
                include = in_prep or bool(tasks) or opp.id in task_opp_ids
            elif scope == "team":
                include = in_prep or bool(tasks)
            elif scope == "unassigned":
                include = unassigned
            else:  # mine
                include = is_responsible or mine_task or (
                    in_prep and (is_responsible or (rid is None and any(
                        t.created_by_id == self.user_id for t in tasks
                    )))
                )
                # Also: user started prep (responsible or created tasks)
                if not include and in_prep and is_responsible:
                    include = True
                if not include and mine_task:
                    include = True
                if not include and is_responsible:
                    include = True
                # started preparation as actor stored in full_info
                actor = (opp.full_info or {}).get("preparation_started_by") or (opp.full_info or {}).get(
                    "interest_user_id"
                )
                if not include and actor and str(actor) == str(self.user_id):
                    include = True

            if not include:
                continue

            if q:
                qq = q.lower()
                blob = f"{opp.code} {opp.institution} {opp.title} {names.get(rid or uuid.UUID(int=0), '')}".lower()
                if qq not in blob and not any(qq in t.title.lower() for t in tasks):
                    continue

            proc_dl = _deadline_as_dt(opp.deadline)
            light, hours = traffic_light(proc_dl, now=now)
            next_t = self._next_pending(tasks)
            rows.append(
                MyLicitacionRow(
                    opportunity_id=opp.id,
                    code=opp.code,
                    institution=opp.institution,
                    title=opp.title,
                    company=opp.company,
                    status=opp.status,
                    status_label=STATUS_LABELS.get(opp.status, opp.status),
                    process_deadline=proc_dl,
                    process_traffic_light=light,  # type: ignore[arg-type]
                    process_hours_remaining=round(hours, 1) if hours is not None else None,
                    responsible_user_id=rid,
                    responsible_name=names.get(rid) if rid else (opp.full_info or {}).get("responsible_name"),
                    checklist_progress=self._progress(tasks),
                    next_pending_title=next_t.title if next_t else None,
                    next_pending_due_at=next_t.due_at if next_t else None,
                    priority=opp.priority or "medium",
                    source_url=opp.source_url,
                )
            )

        rows = rows[:limit]
        summary = self._build_summary(rows, all_tasks, now)
        return MyLicitacionesResponse(summary=summary, items=rows, total=len(rows), scope=scope)

    def _build_summary(
        self, rows: list[MyLicitacionRow], all_tasks: list[DGCPPreparationTask], now: datetime
    ) -> MyWorkSummary:
        today = now.date()
        require = 0
        due3 = 0
        in_prep = 0
        for r in rows:
            if r.process_traffic_light in ("red", "orange", "black"):
                require += 1
            if r.next_pending_due_at:
                nd = r.next_pending_due_at
                if nd.tzinfo is None:
                    nd = nd.replace(tzinfo=UTC)
                if nd.date() <= today:
                    require += 1
            if r.process_hours_remaining is not None and 0 <= r.process_hours_remaining <= 72:
                due3 += 1
            if r.status in PREP_STATUSES:
                in_prep += 1
        overdue = sum(
            1
            for t in all_tasks
            if t.assigned_user_id == self.user_id
            and t.status in OPEN_TASK_STATUSES
            and t.due_at
            and (t.due_at if t.due_at.tzinfo else t.due_at.replace(tzinfo=UTC)) < now
        )
        # new awards: won in last 7d among my rows — soft signal
        new_awards = sum(1 for r in rows if r.status == "won")
        return MyWorkSummary(
            require_attention_today=require,
            due_in_3_days=due3,
            in_preparation=in_prep,
            overdue_tasks=overdue,
            new_awards=new_awards,
        )

    async def list_hoy(self) -> HoyResponse:
        now = datetime.now(UTC)
        today = now.date()
        tomorrow = today + timedelta(days=1)
        items: list[HoyItem] = []

        tasks = list(
            (
                await self.db.execute(
                    select(DGCPPreparationTask).where(
                        DGCPPreparationTask.tenant_id == self.tenant_id,
                        DGCPPreparationTask.assigned_user_id == self.user_id,
                        DGCPPreparationTask.status.in_(list(OPEN_TASK_STATUSES)),
                    )
                )
            ).scalars().all()
        )
        opp_ids = {t.opportunity_id for t in tasks}
        my_lic = await self.list_my_licitations(scope="mine", limit=200)
        for r in my_lic.items:
            opp_ids.add(r.opportunity_id)
        opps = {}
        if opp_ids:
            for o in (
                await self.db.execute(select(DGCPOpportunity).where(DGCPOpportunity.id.in_(list(opp_ids))))
            ).scalars().all():
                opps[o.id] = o

        for t in tasks:
            if not t.due_at:
                continue
            due = t.due_at if t.due_at.tzinfo else t.due_at.replace(tzinfo=UTC)
            opp = opps.get(t.opportunity_id)
            if not opp:
                continue
            if due < now:
                kind, rank = "task_overdue", 1
            elif due.date() == today:
                kind, rank = "task_today", 2
            elif due.date() == tomorrow:
                kind, rank = "task_tomorrow", 3
            elif due <= now + timedelta(days=3):
                kind, rank = "task_soon", 4
            else:
                continue
            items.append(
                HoyItem(
                    kind=kind,  # type: ignore[arg-type]
                    sort_rank=rank,
                    title=t.title,
                    opportunity_id=opp.id,
                    opportunity_code=opp.code,
                    institution=opp.institution,
                    due_at=due,
                    task_id=t.id,
                    priority=t.priority,
                    status=t.status,
                )
            )

        for r in my_lic.items:
            if not r.process_deadline:
                continue
            due = r.process_deadline if r.process_deadline.tzinfo else r.process_deadline.replace(tzinfo=UTC)
            if due.date() == today:
                items.append(
                    HoyItem(
                        kind="process_today",
                        sort_rank=2,
                        title=f"Proceso vence hoy: {r.code}",
                        opportunity_id=r.opportunity_id,
                        opportunity_code=r.code,
                        institution=r.institution,
                        due_at=due,
                        priority=r.priority,
                        status=r.status,
                    )
                )
            elif due.date() == tomorrow:
                items.append(
                    HoyItem(
                        kind="process_tomorrow",
                        sort_rank=3,
                        title=f"Proceso vence mañana: {r.code}",
                        opportunity_id=r.opportunity_id,
                        opportunity_code=r.code,
                        institution=r.institution,
                        due_at=due,
                        priority=r.priority,
                        status=r.status,
                    )
                )

        items.sort(key=lambda x: (x.sort_rank, x.due_at or datetime.max.replace(tzinfo=UTC)))
        return HoyResponse(items=items, total=len(items))

    async def list_my_pendientes(
        self,
        *,
        filter_mode: str = "open",
        company: str | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        q = select(DGCPPreparationTask).where(
            DGCPPreparationTask.tenant_id == self.tenant_id,
            DGCPPreparationTask.assigned_user_id == self.user_id,
        )
        if filter_mode == "completed":
            q = q.where(DGCPPreparationTask.status == "completed")
        elif filter_mode == "overdue":
            q = q.where(
                DGCPPreparationTask.status.in_(list(OPEN_TASK_STATUSES)),
                DGCPPreparationTask.due_at < now,
            )
        elif filter_mode == "today":
            start = datetime(now.year, now.month, now.day, tzinfo=UTC)
            end = start + timedelta(days=1)
            q = q.where(
                DGCPPreparationTask.status.in_(list(OPEN_TASK_STATUSES)),
                DGCPPreparationTask.due_at >= start,
                DGCPPreparationTask.due_at < end,
            )
        elif filter_mode == "week":
            end = now + timedelta(days=7)
            q = q.where(
                DGCPPreparationTask.status.in_(list(OPEN_TASK_STATUSES)),
                or_(DGCPPreparationTask.due_at == None, DGCPPreparationTask.due_at <= end),  # noqa: E711
            )
        else:
            q = q.where(DGCPPreparationTask.status.in_(list(OPEN_TASK_STATUSES)))

        tasks = list((await self.db.execute(q.order_by(DGCPPreparationTask.due_at.asc().nullslast()))).scalars().all())
        opp_ids = {t.opportunity_id for t in tasks}
        opps: dict[uuid.UUID, DGCPOpportunity] = {}
        if opp_ids:
            for o in (
                await self.db.execute(select(DGCPOpportunity).where(DGCPOpportunity.id.in_(list(opp_ids))))
            ).scalars().all():
                if company and o.company != company:
                    continue
                opps[o.id] = o
        if company:
            tasks = [t for t in tasks if t.opportunity_id in opps]
        names = await self._user_names({t.assigned_user_id for t in tasks if t.assigned_user_id})
        return {
            "items": [self._task_out(t, names) for t in tasks],
            "total": len(tasks),
            "opportunity_code": {str(o.id): o.code for o in opps.values()},
            "institution": {str(o.id): o.institution for o in opps.values()},
        }

    # ── alerts ───────────────────────────────────────────────

    async def scan_and_emit_alerts(self) -> dict[str, int]:
        now = datetime.now(UTC)
        created = 0
        skipped = 0
        notif = NotificationService(self.db, self.tenant_id)

        tasks = list(
            (
                await self.db.execute(
                    select(DGCPPreparationTask).where(
                        DGCPPreparationTask.tenant_id == self.tenant_id,
                        DGCPPreparationTask.status.in_(list(OPEN_TASK_STATUSES)),
                        DGCPPreparationTask.due_at.is_not(None),
                        DGCPPreparationTask.assigned_user_id.is_not(None),
                    )
                )
            ).scalars().all()
        )
        opp_ids = {t.opportunity_id for t in tasks}
        opps = {
            o.id: o
            for o in (
                await self.db.execute(select(DGCPOpportunity).where(DGCPOpportunity.id.in_(list(opp_ids))))
            ).scalars().all()
        } if opp_ids else {}

        for t in tasks:
            due = t.due_at if t.due_at and t.due_at.tzinfo else (t.due_at.replace(tzinfo=UTC) if t.due_at else None)
            if not due or not t.assigned_user_id:
                continue
            hours = (due - now).total_seconds() / 3600.0
            if hours < 0:
                alert_type = "task_overdue"
            elif hours <= 24:
                alert_type = "task_due_24h"
            else:
                continue
            opp = opps.get(t.opportunity_id)
            title = f"{t.title} {'vencido' if alert_type == 'task_overdue' else 'vence en 24h'}"
            msg = f"{opp.code if opp else ''} — deadline {due.isoformat()}"
            c, s = await self._emit_alert(
                notif,
                user_id=t.assigned_user_id,
                opportunity_id=t.opportunity_id,
                task_id=t.id,
                alert_type=alert_type,
                deadline=due,
                title=title,
                message=msg,
            )
            created += c
            skipped += s

        # process deadlines for responsible users
        my = await self.list_my_licitations(scope="team", limit=300)
        for r in my.items:
            if not r.process_deadline or not r.responsible_user_id:
                continue
            due = r.process_deadline if r.process_deadline.tzinfo else r.process_deadline.replace(tzinfo=UTC)
            hours = (due - now).total_seconds() / 3600.0
            if 0 <= hours <= 24:
                alert_type = "process_due_24h"
            elif 0 <= hours <= 72:
                alert_type = "process_due_72h"
            else:
                continue
            c, s = await self._emit_alert(
                notif,
                user_id=r.responsible_user_id,
                opportunity_id=r.opportunity_id,
                task_id=None,
                alert_type=alert_type,
                deadline=due,
                title=f"Licitación {r.code} vence en {'24h' if '24' in alert_type else '72h'}",
                message=f"{r.institution} — {due.isoformat()}",
            )
            created += c
            skipped += s

        await self.db.flush()
        return {"created": created, "skipped_duplicates": skipped}

    async def _emit_alert(
        self,
        notif: NotificationService,
        *,
        user_id: uuid.UUID,
        opportunity_id: uuid.UUID,
        task_id: uuid.UUID | None,
        alert_type: str,
        deadline: datetime,
        title: str,
        message: str,
    ) -> tuple[int, int]:
        deadline_key = deadline.strftime("%Y%m%d%H%M")
        dedup = f"{user_id}:{opportunity_id}:{task_id or '-'}:{alert_type}:{deadline_key}"
        exists = (
            await self.db.execute(
                select(DGCPPrepAlertLog).where(
                    DGCPPrepAlertLog.tenant_id == self.tenant_id,
                    DGCPPrepAlertLog.dedup_key == dedup,
                )
            )
        ).scalar_one_or_none()
        if exists:
            return 0, 1
        n = await notif.create(
            user_id=user_id,
            title=title[:255],
            message=message,
            type=NotificationType.DGCP_DEADLINE.value,
            severity="warning" if "overdue" in alert_type or "24" in alert_type else "info",
            related_entity_type="dgcp_opportunity",
            related_entity_id=str(opportunity_id),
        )
        self.db.add(
            DGCPPrepAlertLog(
                tenant_id=self.tenant_id,
                dedup_key=dedup,
                user_id=user_id,
                opportunity_id=opportunity_id,
                task_id=task_id,
                alert_type=alert_type,
                deadline_key=deadline_key,
                notification_id=getattr(n, "id", None),
            )
        )
        return 1, 0

    # ── internals ────────────────────────────────────────────

    async def _get_opp(self, opportunity_id: uuid.UUID) -> DGCPOpportunity:
        opp = (
            await self.db.execute(
                select(DGCPOpportunity).where(
                    DGCPOpportunity.tenant_id == self.tenant_id,
                    DGCPOpportunity.id == opportunity_id,
                )
            )
        ).scalar_one_or_none()
        if not opp:
            raise ValueError("Licitación no encontrada")
        return opp

    async def _get_task(self, task_id: uuid.UUID) -> DGCPPreparationTask:
        task = (
            await self.db.execute(
                select(DGCPPreparationTask).where(
                    DGCPPreparationTask.tenant_id == self.tenant_id,
                    DGCPPreparationTask.id == task_id,
                )
            )
        ).scalar_one_or_none()
        if not task:
            raise ValueError("Pendiente no encontrado")
        return task
