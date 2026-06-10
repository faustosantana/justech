"""Panel ejecutivo — agregación cross-módulo para /dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.price_list import PriceListProduct, PriceQuoteDraft
from app.models.task import Task
from app.models.user import User
from app.schemas.dashboard import (
    ExecutiveActivityItem,
    ExecutiveAlert,
    ExecutiveDashboardResponse,
    ExecutiveKpi,
    ModuleSnapshot,
)
from app.services.dgcp_service import DGCPService
from app.services.document_service import DocumentService
from app.services.m365_service import M365Service
from app.services.odoo_service import OdooService
from app.services.work_service import WorkService


class ExecutiveDashboardService:
    ASSISTANT_SUGGESTIONS = [
        "¿Cuánto nos debe Banco Ademi?",
        "¿Qué licitaciones de computadoras hay?",
        "¿Quién tiene mejor precio laptop 16GB 512GB?",
        "¿Qué documentos están vencidos?",
        "¿Qué tareas tiene Jennipher?",
    ]

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def get_dashboard(self, user: User, tenant_name: str) -> ExecutiveDashboardResponse:
        odoo = OdooService(self.db, self.tenant_id, user_id=self.user_id)
        dgcp = DGCPService(self.db)
        docs = DocumentService(self.db, self.tenant_id, self.user_id)
        work = WorkService(self.db, self.tenant_id, self.user_id)
        m365 = M365Service(self.db, self.tenant_id, user_id=self.user_id)

        odoo_summary = await odoo.summary()
        dgcp_summary = await dgcp.compute_dashboard(self.tenant_id, user_id=self.user_id)
        doc_health = await docs.health()
        work_hub = await work.get_hub()
        m365_health = await m365.health()

        overdue_tasks = await self._tenant_overdue_tasks()
        price_products = await self._count_price_products()
        quote_drafts = await self._count_quote_drafts()
        critical_notifications = await self._critical_notifications()
        kpis = self._build_kpis(
            odoo_summary,
            dgcp_summary,
            doc_health,
            work_hub,
            overdue_tasks,
            price_products,
            quote_drafts,
            critical_notifications,
        )
        modules = self._build_modules(odoo_summary, dgcp_summary, doc_health, work_hub, m365_health)
        alerts = self._build_alerts(doc_health, work_hub, dgcp_summary, odoo_summary, overdue_tasks)
        activity = self._build_activity(work_hub)
        proactive = self._proactive_message(user, work_hub, dgcp_summary, doc_health, overdue_tasks)

        first_name = (user.full_name or user.email.split("@")[0]).split()[0]
        return ExecutiveDashboardResponse(
            user_name=first_name,
            tenant_name=tenant_name,
            company_name=odoo_summary.company_name,
            updated_at=datetime.now(timezone.utc),
            proactive_message=proactive,
            assistant_suggestions=self.ASSISTANT_SUGGESTIONS,
            kpis=kpis,
            modules=modules,
            alerts=alerts,
            activity=activity,
        )

    async def _tenant_overdue_tasks(self) -> int:
        today = datetime.now(timezone.utc).date()
        result = await self.db.execute(
            select(func.count(Task.id)).where(
                Task.tenant_id == self.tenant_id,
                Task.status.notin_(["completada", "cancelada"]),
                Task.due_date.is_not(None),
                Task.due_date < today,
            )
        )
        return int(result.scalar() or 0)

    async def _count_price_products(self) -> int:
        result = await self.db.execute(
            select(func.count(PriceListProduct.id)).where(
                PriceListProduct.tenant_id == self.tenant_id,
                PriceListProduct.is_current.is_(True),
            )
        )
        return int(result.scalar() or 0)

    async def _count_quote_drafts(self) -> int:
        result = await self.db.execute(
            select(func.count(PriceQuoteDraft.id)).where(
                PriceQuoteDraft.tenant_id == self.tenant_id,
            )
        )
        return int(result.scalar() or 0)

    async def _critical_notifications(self) -> int:
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.tenant_id == self.tenant_id,
                Notification.user_id == self.user_id,
                Notification.is_read.is_(False),
                Notification.severity.in_(["high", "critical", "warning"]),
            )
        )
        return int(result.scalar() or 0)

    def _build_kpis(
        self,
        odoo,
        dgcp,
        doc_health,
        work_hub,
        overdue_tasks,
        price_products: int,
        quote_drafts: int,
        critical_notifications: int,
    ) -> list[ExecutiveKpi]:
        return [
            ExecutiveKpi(
                id="sales_month",
                label="Ventas del mes (cotiz.)",
                value=str(odoo.quotations),
                source="Odoo",
                href="/odoo",
                tone="primary",
            ),
            ExecutiveKpi(
                id="receivables",
                label="Cuentas por cobrar",
                value=str(odoo.open_invoices),
                source="Odoo",
                href="/odoo",
                tone="warning" if odoo.open_invoices else "muted",
            ),
            ExecutiveKpi(
                id="overdue_invoices",
                label="Facturas vencidas",
                value=str(odoo.overdue_invoices),
                source="Odoo",
                href="/odoo",
                tone="danger" if odoo.overdue_invoices else "success",
            ),
            ExecutiveKpi(
                id="quotations",
                label="Cotizaciones pendientes",
                value=str(odoo.quotations),
                source="Odoo",
                href="/odoo",
                tone="warning" if odoo.quotations else "muted",
            ),
            ExecutiveKpi(
                id="dgcp_active",
                label="Licitaciones vigentes",
                value=str(dgcp.total_opportunities),
                source="DGCP",
                href="/dgcp",
                tone="primary",
            ),
            ExecutiveKpi(
                id="dgcp_bid",
                label="Para licitar",
                value=str(dgcp.to_bid),
                source="DGCP",
                href="/dgcp",
                tone="warning" if dgcp.to_bid else "muted",
            ),
            ExecutiveKpi(
                id="documents_review",
                label="Documentos por revisar",
                value=str(doc_health.alerts_open),
                source="Documentos",
                href="/documents",
                tone="warning" if doc_health.alerts_open else "success",
            ),
            ExecutiveKpi(
                id="tasks_overdue",
                label="Tareas vencidas",
                value=str(overdue_tasks or work_hub.my_overdue),
                source="Tareas",
                href="/tasks",
                tone="danger" if (overdue_tasks or work_hub.my_overdue) else "success",
            ),
            ExecutiveKpi(
                id="my_pending",
                label="Mis tareas pendientes",
                value=str(work_hub.my_pending),
                source="Centro de trabajo",
                href="/work",
                tone="primary",
            ),
            ExecutiveKpi(
                id="price_products",
                label="Productos indexados",
                value=str(price_products),
                source="Precios",
                href="/prices",
                tone="primary",
            ),
            ExecutiveKpi(
                id="quote_drafts",
                label="Borradores cotización",
                value=str(quote_drafts),
                source="Precios",
                href="/prices/drafts",
                tone="warning" if quote_drafts else "muted",
            ),
            ExecutiveKpi(
                id="critical_notifications",
                label="Notificaciones críticas",
                value=str(critical_notifications),
                source="Notificaciones",
                href="/notifications",
                tone="danger" if critical_notifications else "success",
            ),
        ]

    def _build_modules(self, odoo, dgcp, doc_health, work_hub, m365_health) -> list[ModuleSnapshot]:
        return [
            ModuleSnapshot(
                id="odoo",
                label="Odoo",
                status="Conectado" if odoo.connected else "No conectado",
                metrics=[
                    f"{odoo.customers} clientes",
                    f"{odoo.open_invoices} facturas abiertas",
                    f"{odoo.quotations} cotizaciones",
                ],
                href="/odoo",
            ),
            ModuleSnapshot(
                id="dgcp",
                label="DGCP",
                status="Operativo",
                metrics=[
                    f"{dgcp.to_bid} para licitar",
                    f"{dgcp.to_review} en revisión",
                    f"{dgcp.total_opportunities} oportunidades",
                ],
                href="/dgcp",
            ),
            ModuleSnapshot(
                id="documents",
                label="Documentos",
                status="Operativo",
                metrics=[
                    f"{doc_health.documents_count} documentos",
                    f"{doc_health.alerts_open} alertas abiertas",
                ],
                href="/documents",
            ),
            ModuleSnapshot(
                id="tasks",
                label="Tareas",
                status="Operativo",
                metrics=[
                    f"{work_hub.my_pending} pendientes",
                    f"{work_hub.my_overdue} vencidas",
                    f"{work_hub.my_critical} críticas",
                ],
                href="/tasks",
            ),
            ModuleSnapshot(
                id="m365",
                label="Microsoft 365",
                status="Conectado" if m365_health.connected else "No conectado",
                metrics=[m365_health.message or "Estado de integración"],
                href="/m365",
            ),
        ]

    def _build_alerts(self, doc_health, work_hub, dgcp, odoo, overdue_tasks) -> list[ExecutiveAlert]:
        alerts: list[ExecutiveAlert] = []
        if doc_health.alerts_open:
            alerts.append(ExecutiveAlert(
                id="doc-alerts",
                title=f"{doc_health.alerts_open} alerta(s) documental(es) abiertas",
                priority="warning",
                source="Documentos",
                href="/documents",
            ))
        if overdue_tasks or work_hub.my_overdue:
            count = overdue_tasks or work_hub.my_overdue
            alerts.append(ExecutiveAlert(
                id="tasks-overdue",
                title=f"{count} tarea(s) vencida(s)",
                priority="danger",
                source="Tareas",
                href="/tasks",
            ))
        if dgcp.to_bid:
            alerts.append(ExecutiveAlert(
                id="dgcp-bid",
                title=f"{dgcp.to_bid} licitación(es) listas para licitar",
                priority="warning",
                source="DGCP",
                href="/dgcp",
            ))
        if odoo.overdue_invoices:
            alerts.append(ExecutiveAlert(
                id="odoo-overdue",
                title=f"{odoo.overdue_invoices} factura(s) vencida(s)",
                priority="danger",
                source="Odoo",
                href="/odoo",
            ))
        if not odoo.connected:
            alerts.append(ExecutiveAlert(
                id="odoo-offline",
                title="Odoo no conectado — ventas y CxC no disponibles",
                priority="warning",
                source="Odoo",
                href="/odoo/settings",
            ))
        return alerts[:8]

    def _build_activity(self, work_hub) -> list[ExecutiveActivityItem]:
        items: list[ExecutiveActivityItem] = []
        for entry in work_hub.recent_activity[:8]:
            items.append(ExecutiveActivityItem(
                id=entry.task_id or entry.action,
                title=entry.task_title or entry.action,
                subtitle=entry.user_name or "Centro de trabajo",
                timestamp=entry.created_at,
                href=f"/tasks/{entry.task_id}" if entry.task_id else "/work",
            ))
        for note in work_hub.recent_notifications[:4]:
            items.append(ExecutiveActivityItem(
                id=str(note.id),
                title=note.title,
                subtitle=note.message[:80] if note.message else "Notificación",
                timestamp=note.created_at.isoformat() if note.created_at else None,
                href="/notifications",
            ))
        return items[:10]

    def _proactive_message(self, user, work_hub, dgcp, doc_health, overdue_tasks) -> str:
        first = (user.full_name or user.email.split("@")[0]).split()[0]
        parts: list[str] = []
        overdue = overdue_tasks or work_hub.my_overdue
        if overdue:
            parts.append(f"{overdue} tarea(s) vencida(s)")
        if dgcp.to_bid:
            parts.append(f"{dgcp.to_bid} licitación(es) próximas a acción")
        if doc_health.alerts_open:
            parts.append(f"{doc_health.alerts_open} documento(s) que requieren revisión")
        if not parts:
            return (
                f"Hola {first}, encontré información importante para revisar hoy. "
                "¿Quieres que te ayude con prioridades?"
            )
        joined = ", ".join(parts)
        return (
            f"Buenos días, {first}. Detecté {joined}. "
            "¿Quieres que te muestre el resumen?"
        )
