"""Copilot Briefing — resumen proactivo Assistant 3.0."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.user import User
from app.schemas.assistant import (
    CopilotBriefingItem,
    CopilotBriefingResponse,
    CopilotBriefingSection,
    CopilotQuickAction,
)
from app.services.dgcp_service import DGCPService
from app.services.document_service import DocumentService
from app.services.odoo_service import OdooService
from app.config import settings
from app.services.m365_operative_service import M365OperativeService
from app.services.work_service import WorkService
from app.services.assistant_synthesis_service import AssistantSynthesisService


class CopilotBriefingService:
    """Genera briefing ejecutivo al abrir el copiloto."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def get_briefing(self, user: User, *, mode: str = "managerial") -> CopilotBriefingResponse:
        work = WorkService(self.db, self.tenant_id, self.user_id)
        dgcp = DGCPService(self.db)
        docs = DocumentService(self.db, self.tenant_id, self.user_id)
        odoo = OdooService(self.db, self.tenant_id, user_id=self.user_id)

        hub = await work.get_hub()
        dgcp_summary = await dgcp.compute_dashboard(self.tenant_id, user_id=self.user_id)
        doc_health = await docs.health()
        odoo_summary = await odoo.summary()
        tenant_overdue = await self._tenant_overdue_tasks()

        first = (user.full_name or user.email.split("@")[0]).split()[0]
        hour = datetime.now(timezone.utc).hour
        greeting = "Buenos días" if hour < 12 else ("Buenas tardes" if hour < 18 else "Buenas noches")

        priorities: list[CopilotBriefingItem] = []
        alerts: list[CopilotBriefingItem] = []
        opportunities: list[CopilotBriefingItem] = []
        recommendations: list[CopilotBriefingItem] = []
        quick_actions: list[CopilotQuickAction] = []
        activity: list[CopilotBriefingItem] = []

        overdue = tenant_overdue or hub.my_overdue
        if overdue:
            priorities.append(CopilotBriefingItem(
                label=f"{overdue} tarea(s) vencida(s)",
                detail="Requieren acción inmediata",
                severity="critical",
                href="/tasks",
            ))
            quick_actions.append(CopilotQuickAction(
                label="Ver tareas vencidas",
                question="¿Qué tareas vencidas tengo?",
                href="/tasks",
            ))

        if dgcp_summary.to_bid:
            opportunities.append(CopilotBriefingItem(
                label=f"{dgcp_summary.to_bid} licitación(es) activas",
                detail="Próximas a presentación o seguimiento",
                href="/dgcp",
            ))
            quick_actions.append(CopilotQuickAction(
                label="Ver licitaciones",
                question="¿Qué licitaciones activas hay?",
                href="/dgcp",
            ))

        if doc_health.alerts_open:
            alerts.append(CopilotBriefingItem(
                label=f"{doc_health.alerts_open} documento(s) vencidos o por vencer",
                detail="Revisión documental requerida",
                severity="warning",
                href="/documents",
            ))

        if hub.my_critical:
            priorities.append(CopilotBriefingItem(
                label=f"{hub.my_critical} tarea(s) crítica(s)",
                detail="Prioridad alta asignada a ti",
                severity="critical",
                href="/tasks",
            ))

        if hub.unread_notifications:
            alerts.append(CopilotBriefingItem(
                label=f"{hub.unread_notifications} notificación(es) sin leer",
                href="/notifications",
            ))

        recommendations.append(CopilotBriefingItem(
            label="Banco Ademi — revisar cotizaciones y CxC",
            detail="Cliente frecuente con actividad comercial",
            question="¿Qué le hemos vendido a Banco Ademi?",
        ))
        recommendations.append(CopilotBriefingItem(
            label="Capital DBG — seguimiento financiero",
            detail="Verificar facturas pendientes",
            question="¿Cuánto nos debe Capital DBG?",
        ))

        for act in hub.recent_activity[:5]:
            activity.append(CopilotBriefingItem(
                label=act.action,
                detail=act.task_title,
                href=f"/tasks/{act.task_id}" if act.task_id else "/work",
            ))

        if mode == "operational":
            quick_actions.extend([
                CopilotQuickAction(label="Cotizaciones pendientes", question="¿Qué cotizaciones están pendientes?", href="/odoo"),
                CopilotQuickAction(label="Mis seguimientos", question="¿Qué tareas tengo pendientes?", href="/tasks"),
            ])
            if hub.my_due_soon:
                priorities.append(CopilotBriefingItem(
                    label=f"{hub.my_due_soon} tarea(s) por vencer en 3 días",
                    href="/tasks",
                ))
        elif mode == "bidding":
            quick_actions.extend([
                CopilotQuickAction(label="Ofertas económicas", question="¿Qué licitaciones necesitan oferta económica?", href="/dgcp"),
                CopilotQuickAction(label="Expedientes incompletos", question="¿Qué expedientes están incompletos?", href="/dgcp"),
            ])
            if doc_health.alerts_open:
                opportunities.append(CopilotBriefingItem(
                    label="Documentos faltantes o vencidos",
                    detail="Revisar antes de presentación",
                    question="¿Qué documentos están vencidos?",
                    href="/documents",
                ))

        if settings.m365_operative_enabled:
            m365_stats = await M365OperativeService(
                self.db, self.tenant_id, self.user_id
            ).get_briefing_stats()
            if m365_stats.get("quotes"):
                priorities.append(CopilotBriefingItem(
                    label=f"{m365_stats['quotes']} cotización(es) proveedor por correo",
                    detail="Microsoft 365 Operativo",
                    href="/m365/operativo",
                ))
            if m365_stats.get("purchase_orders"):
                alerts.append(CopilotBriefingItem(
                    label=f"{m365_stats['purchase_orders']} orden(es) de compra detectadas",
                    href="/m365/operativo",
                ))
            if m365_stats.get("vendor_invoices"):
                alerts.append(CopilotBriefingItem(
                    label=f"{m365_stats['vendor_invoices']} factura(s) proveedor",
                    href="/m365/operativo",
                ))
            if m365_stats.get("dgcp_docs"):
                opportunities.append(CopilotBriefingItem(
                    label=f"{m365_stats['dgcp_docs']} documento(s) DGCP en bandeja",
                    href="/m365/operativo",
                ))
            quick_actions.extend([
                CopilotQuickAction(label="Ver correos importantes", href="/m365/operativo"),
                CopilotQuickAction(label="Adjuntar documentos", href="/m365/operativo"),
                CopilotQuickAction(label="Crear ofertas", href="/dgcp"),
            ])

        summary_lines: list[str] = []
        for bucket in (priorities, alerts, opportunities):
            for item in bucket[:3]:
                summary_lines.append(f"• {item.label}")

        if not summary_lines:
            summary_lines.append("• Sin alertas críticas — puedo ayudarte con ventas, licitaciones o documentos")

        headline = (
            f"{greeting}, {first}.\n\nDetecté:\n\n"
            + "\n".join(summary_lines[:6])
            + "\n\n¿Deseas que te muestre el resumen?"
        )

        if mode == "operational":
            headline = (
                f"{greeting}, {first}. Tienes {hub.my_pending} pendiente(s), "
                f"{hub.my_in_progress} en proceso y {hub.my_due_soon} por vencer pronto."
            )
        elif mode == "bidding":
            headline = (
                f"{greeting}, {first}. {dgcp_summary.to_bid} licitación(es) activas "
                f"y {doc_health.alerts_open} alerta(s) documentales."
            )

        if mode == "managerial" and settings.m365_operative_enabled:
            m365_stats = await M365OperativeService(
                self.db, self.tenant_id, self.user_id
            ).get_briefing_stats()
            m365_bullets = [
                line for line in (m365_stats.get("lines") or []) if line.startswith("•")
            ]
            if m365_bullets:
                headline = (
                    f"{greeting}, {first}.\n\n"
                    + (m365_stats.get("lines") or [""])[0]
                    + "\n\nDetecté:\n\n"
                    + "\n".join(m365_bullets[:6])
                    + "\n\nAcciones sugeridas: revisar bandeja M365 Operativo."
                )

        synthesizer = AssistantSynthesisService(self.db, self.tenant_id)
        briefing_facts = {
            "modo": mode,
            "tareas_vencidas": overdue,
            "licitaciones_activas": dgcp_summary.to_bid,
            "documentos_alerta": doc_health.alerts_open,
            "notificaciones": hub.unread_notifications,
            "pendientes": hub.my_pending,
            "empresa_odoo": odoo_summary.company_name,
        }
        headline = await synthesizer.synthesize_briefing_greeting(
            template_greeting=headline,
            facts=briefing_facts,
            mode=mode,
            user_first_name=first,
        )

        return CopilotBriefingResponse(
            greeting=headline,
            mode=mode,
            company_name=odoo_summary.company_name,
            updated_at=datetime.now(timezone.utc),
            priorities=CopilotBriefingSection(title="Prioridades", items=priorities),
            alerts=CopilotBriefingSection(title="Alertas", items=alerts),
            opportunities=CopilotBriefingSection(title="Oportunidades", items=opportunities),
            recommendations=CopilotBriefingSection(title="Recomendaciones", items=recommendations),
            quick_actions=quick_actions[:8],
            recent_activity=CopilotBriefingSection(title="Últimas actividades", items=activity),
        )

    async def _tenant_overdue_tasks(self) -> int:
        today = datetime.now(timezone.utc).date()
        result = await self.db.execute(
            select(func.count(Task.id)).where(
                Task.tenant_id == self.tenant_id,
                Task.status.notin_(["completada", "cancelada"]),
                Task.due_date.isnot(None),
                Task.due_date < today,
            )
        )
        return int(result.scalar() or 0)
