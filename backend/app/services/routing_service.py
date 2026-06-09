"""Operational Routing Engine — asignación automática de tareas."""

from __future__ import annotations

import re
import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import TenantMembership
from app.models.user import User
from app.schemas.routing import RoutingPreviewResponse
from app.scripts.seed import SUPERVISOR_BY_ASSIGNEE


class RoutingService:
    """Motor de reglas operacionales Justech."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def preview(
        self,
        *,
        event_type: str,
        title: str = "",
        description: str = "",
        customer_name: str | None = None,
        amount: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RoutingPreviewResponse:
        meta = metadata or {}
        text = f"{title} {description}".lower()
        event = event_type.lower().strip()

        result = self._route(event, text, meta)
        assignee_name = result["assignee"]
        supervisor_name = self._supervisor_for(assignee_name)
        assignee_id = await self.resolve_assignee_id(assignee_name)
        supervisor_id = await self.resolve_assignee_id(supervisor_name)
        warning = None
        if assignee_name and not assignee_id:
            warning = f"No se encontró usuario JAIOS para «{assignee_name}». Asigne manualmente."
        return RoutingPreviewResponse(
            event_type=event_type,
            category=result["category"],
            department=result["department"],
            priority=result["priority"],
            suggested_assignee_name=assignee_name,
            suggested_supervisor_name=supervisor_name,
            assignee_resolved=assignee_id is not None,
            supervisor_resolved=supervisor_id is not None,
            resolution_warning=warning,
            due_date=result["due_date"],
            notification_message=result["notification"],
            checklist=result["checklist"],
            matched_rule=result["rule"],
        )

    @staticmethod
    def _supervisor_for(assignee_name: str | None) -> str | None:
        if not assignee_name:
            return None
        for key, supervisor in SUPERVISOR_BY_ASSIGNEE.items():
            if key.lower() in assignee_name.lower():
                return supervisor
        return None

    def _route(self, event_type: str, text: str, meta: dict[str, Any]) -> dict[str, Any]:
        overdue_days = int(meta.get("overdue_days") or meta.get("days_overdue") or 0)
        dgcp_score = float(meta.get("dgcp_score") or meta.get("score") or 0)
        delivery_days = int(meta.get("delivery_days") or 7)

        rules: list[tuple[bool, dict[str, Any]]] = [
            (
                event_type in ("quotation_request", "cotizacion", "solicitud_cotizacion")
                or "cotizacion" in text
                or "cotización" in text,
                {
                    "rule": "solicitud_cotizacion",
                    "category": "cotizacion",
                    "department": "ventas",
                    "assignee": "Marieli",
                    "priority": "media",
                    "due_hours": 24,
                    "notification": "Nueva solicitud de cotización asignada",
                    "checklist": [
                        "Validar requerimiento del cliente",
                        "Preparar cotización",
                        "Revisar precios y márgenes",
                        "Enviar cotización al cliente",
                    ],
                },
            ),
            (
                event_type in ("vendor_invoice", "factura_proveedor", "supplier_invoice")
                or "factura de proveedor" in text
                or "factura proveedor" in text,
                {
                    "rule": "factura_proveedor",
                    "category": "factura_proveedor",
                    "department": "administracion",
                    "assignee": "Diana",
                    "priority": "alta",
                    "due_hours": 24,
                    "notification": "Nueva factura de proveedor para registrar",
                    "checklist": [
                        "Validar proveedor",
                        "Validar RNC",
                        "Validar monto",
                        "Registrar factura en Odoo",
                        "Adjuntar comprobante",
                    ],
                },
            ),
            (
                event_type in ("customer_invoice", "factura_cliente", "emit_invoice")
                or "factura a cliente" in text
                or "factura cliente" in text
                or "emitir factura" in text,
                {
                    "rule": "factura_cliente",
                    "category": "factura_cliente",
                    "department": "facturacion",
                    "assignee": "Jennipher",
                    "priority": "alta",
                    "due_hours": 8,
                    "notification": "Nueva factura de cliente para emitir",
                    "checklist": [
                        "Validar cotización / orden",
                        "Validar cliente",
                        "Generar factura",
                        "Enviar factura al cliente",
                    ],
                },
            ),
            (
                event_type in ("payment_registration", "pago_cliente", "registrar_pago")
                or "registrar pago" in text
                or "pago de cliente" in text,
                {
                    "rule": "pago_cliente",
                    "category": "pago_cliente",
                    "department": "finanzas",
                    "assignee": "Jennipher",
                    "priority": "alta",
                    "due_hours": 8,
                    "notification": "Nuevo pago de cliente para registrar",
                    "checklist": [
                        "Validar comprobante",
                        "Identificar factura",
                        "Registrar pago",
                        "Confirmar balance pendiente",
                    ],
                },
            ),
            (
                event_type in ("collections", "cuenta_por_cobrar", "invoice_overdue", "cobro")
                or "cuenta por cobrar" in text
                or "factura vencida" in text
                or "cobro" in text
                or overdue_days > 0,
                {
                    "rule": "cuenta_por_cobrar",
                    "category": "cuenta_por_cobrar",
                    "department": "facturacion",
                    "assignee": "Jennipher",
                    "priority": self._collections_priority(overdue_days),
                    "due_hours": 24,
                    "notification": "Seguimiento de cuenta por cobrar asignado",
                    "checklist": [
                        "Contactar cliente",
                        "Enviar estado de cuenta",
                        "Registrar respuesta",
                        "Escalar si aplica",
                    ],
                },
            ),
            (
                event_type in ("support", "soporte", "support_ticket")
                or "soporte" in text
                or "ticket" in text,
                {
                    "rule": "soporte",
                    "category": "soporte",
                    "department": "soporte",
                    "assignee": self._support_assignee(text),
                    "priority": self._support_priority(text),
                    "due_hours": 4 if self._support_priority(text) == "critica" else 24,
                    "notification": "Nueva solicitud de soporte asignada",
                    "checklist": [
                        "Validar cliente",
                        "Diagnosticar",
                        "Asignar técnico",
                        "Registrar solución",
                        "Cerrar caso",
                    ],
                },
            ),
            (
                event_type in ("dgcp_bid", "licitacion", "dgcp_opportunity")
                or "licitacion" in text
                or "licitación" in text
                or "dgcp" in text,
                {
                    "rule": "licitacion",
                    "category": "licitacion",
                    "department": "licitaciones",
                    "assignee": "Fausto",
                    "priority": self._dgcp_priority(dgcp_score, meta.get("days_to_deadline")),
                    "due_hours": 48,
                    "notification": "Nueva oportunidad de licitación para revisar",
                    "checklist": [
                        "Revisar pliego",
                        "Validar documentos legales",
                        "Validar precios",
                        "Preparar oferta",
                        "Revisión gerencia",
                    ],
                },
            ),
            (
                event_type in ("purchase", "compra", "purchase_order")
                or "compra" in text
                or "licencia" in text
                or "equipo" in text,
                {
                    "rule": "compra",
                    "category": "compra",
                    "department": "compras",
                    "assignee": "Diana",
                    "priority": "alta" if delivery_days <= 3 else "media",
                    "due_hours": delivery_days * 24,
                    "notification": "Nueva solicitud de compra asignada",
                    "checklist": [
                        "Validar proveedor",
                        "Comparar precios",
                        "Confirmar disponibilidad",
                        "Generar orden de compra",
                        "Coordinar entrega",
                    ],
                },
            ),
            (
                event_type in ("administration", "administracion", "document", "contrato")
                or "administracion" in text
                or "administración" in text
                or "contrato" in text
                or "certificacion" in text,
                {
                    "rule": "administracion",
                    "category": "administracion",
                    "department": "administracion",
                    "assignee": "Administración",
                    "priority": "media",
                    "due_hours": 72,
                    "notification": "Nueva tarea administrativa asignada",
                    "checklist": [
                        "Revisar documento",
                        "Validar vencimiento",
                        "Archivar",
                        "Notificar",
                    ],
                },
            ),
        ]

        for matched, rule in rules:
            if matched:
                due = date.today() + timedelta(hours=rule.get("due_hours", 24) // 24 or 1)
                if rule.get("due_hours", 24) <= 8:
                    due = date.today()
                return {**rule, "due_date": due}

        return {
            "rule": "default",
            "category": "otro",
            "department": "operaciones",
            "assignee": None,
            "priority": "media",
            "due_hours": 48,
            "due_date": date.today() + timedelta(days=2),
            "notification": "Nueva tarea operativa creada",
            "checklist": [],
        }

    @staticmethod
    def _collections_priority(overdue_days: int) -> str:
        if overdue_days >= 31:
            return "critica"
        if overdue_days >= 8:
            return "alta"
        if overdue_days >= 1:
            return "media"
        return "media"

    @staticmethod
    def _support_priority(text: str) -> str:
        if any(k in text for k in ("critico", "crítico", "caido", "caído", "sin servicio", "down")):
            return "critica"
        if "urgente" in text:
            return "alta"
        return "media"

    @staticmethod
    def _support_assignee(text: str) -> str:
        if "jesus" in text or "jesús" in text:
            return "Jesús"
        return "Felipe Mejía"

    @staticmethod
    def _dgcp_priority(score: float, days_to_deadline: Any) -> str:
        days = int(days_to_deadline) if days_to_deadline is not None else 14
        if days <= 3 or score >= 80:
            return "critica"
        if days <= 7 or score >= 60:
            return "alta"
        return "media"

    async def resolve_assignee_id(self, assignee_name: str | None) -> uuid.UUID | None:
        if not assignee_name:
            return None
        pattern = assignee_name.split("/")[0].strip()
        result = await self.db.execute(
            select(User)
            .join(TenantMembership, TenantMembership.user_id == User.id)
            .where(
                TenantMembership.tenant_id == self.tenant_id,
                User.is_active.is_(True),
                User.full_name.ilike(f"%{pattern}%"),
            )
            .limit(1)
        )
        user = result.scalar_one_or_none()
        return user.id if user else None

    async def resolve_supervisor_id(self, assignee_name: str | None) -> uuid.UUID | None:
        return await self.resolve_assignee_id(self._supervisor_for(assignee_name))
