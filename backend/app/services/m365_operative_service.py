"""Orquestador Microsoft 365 Operativo — ingestión, análisis, acciones."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.economic_offer_draft import EconomicOfferDraft
from app.models.m365_account import M365UserAccount
from app.models.m365_operative import (
    M365AutomationEvent,
    M365EmailActionLog,
    M365MonitoredMailbox,
    M365ProcessedEmail,
)
from app.models.user import User
from app.schemas.m365_operative import (
    M365CalendarSuggestionsResponse,
    M365ExecuteActionResponse,
    M365InboundEmailWebhook,
    M365OperativeDashboard,
    M365ProcessedEmailListResponse,
    M365ProcessedEmailResponse,
    M365SuggestedAction,
    M365SyncResponse,
)
from app.schemas.tasks import TaskFromEventRequest
from app.services.audit_service import AuditService
from app.services.credential_vault import decrypt_secret
from app.services.m365_calendar_intelligence_service import M365CalendarIntelligenceService
from app.services.m365_email_classifier import M365EmailClassifier
from app.services.m365_email_extraction_service import M365EmailExtractionService
from app.services.m365_email_relation_service import M365EmailRelationService
from app.services.m365_operative_demo_inbox import demo_inbox_messages
from app.services.m365_sharepoint_archive_service import M365SharePointArchiveService
from app.services.m365_teams_notification_service import M365TeamsNotificationService
from app.services.notification_service import NotificationService
from app.services.task_service import TaskService
from integrations.microsoft365.client import M365Client
from integrations.microsoft365.config import M365Config
from integrations.microsoft365.imap_client import M365ImapService, map_imap_error


ACTION_CATALOG: dict[str, tuple[str, str]] = {
    "attach_to_process": ("Adjuntar al expediente", "Vincula el correo y adjuntos al proceso DGCP relacionado."),
    "create_economic_offer": ("Crear oferta económica", "Genera borrador de oferta económica para la licitación."),
    "save_to_expediente": ("Guardar en expediente", "Archiva documentos en el expediente DGCP activo."),
    "create_task": ("Crear tarea", "Crea tarea operativa con routing automático."),
    "archive_sharepoint": ("Guardar en SharePoint", "Archiva en carpeta corporativa e indexa en Hermes."),
    "notify_teams": ("Notificar en Teams", "Envía alerta al equipo vía Teams/n8n."),
    "send_to_cxp": ("Enviar a CxP", "Deriva factura proveedor a cuentas por pagar."),
    "notify_cxc": ("Notificar CxC", "Actualiza seguimiento de cobro al cliente."),
    "save_as_quote": ("Guardar como cotización", "Registra cotización proveedor para comparación."),
}


class M365OperativeService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._classifier = M365EmailClassifier()
        self._extractor = M365EmailExtractionService()
        self._relations = M365EmailRelationService(db, tenant_id)
        self._sharepoint = M365SharePointArchiveService()
        self._calendar = M365CalendarIntelligenceService()
        self._audit = AuditService(db)

    def _graph_api_configured(self) -> bool:
        cfg = M365Config(
            tenant_id=settings.m365_tenant_id,
            client_id=settings.m365_client_id,
            client_secret=settings.m365_client_secret,
            redirect_uri=settings.m365_redirect_uri,
            read_only=settings.m365_read_only,
        )
        return cfg.is_configured() and not settings.m365_operative_demo_mode

    async def _get_imap_account(self) -> M365UserAccount | None:
        if not self.user_id:
            return None
        result = await self.db.execute(
            select(M365UserAccount).where(
                M365UserAccount.tenant_id == self.tenant_id,
                M365UserAccount.jaios_user_id == self.user_id,
                M365UserAccount.connection_mode == "imap",
                M365UserAccount.connection_status == "connected",
                M365UserAccount.is_active.is_(True),
            )
        )
        acc = result.scalar_one_or_none()
        if acc and acc.imap_password_encrypted and acc.email:
            return acc
        return None

    async def mailbox_connected(self) -> bool:
        return (await self._get_imap_account()) is not None

    async def ensure_mailboxes(self) -> None:
        addresses = list(settings.m365_monitored_mailbox_list)
        imap_acc = await self._get_imap_account()
        if imap_acc and imap_acc.email:
            addresses.append(imap_acc.email)
        for address in dict.fromkeys(addresses):
            existing = await self.db.execute(
                select(M365MonitoredMailbox).where(
                    M365MonitoredMailbox.tenant_id == self.tenant_id,
                    M365MonitoredMailbox.address == address,
                )
            )
            if existing.scalar_one_or_none() is None:
                self.db.add(
                    M365MonitoredMailbox(
                        tenant_id=self.tenant_id,
                        address=address,
                        display_name=address.split("@")[0].title(),
                    )
                )
        await self.db.flush()

    async def _mail_source_flags(self) -> tuple[bool, bool]:
        imap = await self.mailbox_connected()
        graph = self._graph_api_configured()
        real = imap or graph
        demo = settings.m365_operative_demo_mode and not real
        return real, demo

    async def sync_inbox(self) -> M365SyncResponse:
        await self.ensure_mailboxes()
        ingested = processed = skipped = 0
        messages: list[dict] = []
        imap_acc = await self._get_imap_account()
        using_imap = False
        using_graph = False
        demo = False

        if imap_acc:
            using_imap = True
            try:
                password = decrypt_secret(imap_acc.imap_password_encrypted or "")
                imap = M365ImapService(
                    host=imap_acc.imap_host or settings.m365_imap_host,
                    port=imap_acc.imap_port or settings.m365_imap_port,
                )
                messages = await asyncio.to_thread(
                    imap.fetch_recent,
                    email_address=imap_acc.email or "",
                    password=password,
                    limit=50,
                )
                imap_acc.last_sync_at = datetime.now(timezone.utc)
            except Exception as exc:
                await self.db.commit()
                raise ValueError(map_imap_error(exc)) from exc
        elif self._graph_api_configured():
            using_graph = True
            client = M365Client(
                M365Config(
                    tenant_id=settings.m365_tenant_id,
                    client_id=settings.m365_client_id,
                    client_secret=settings.m365_client_secret,
                    redirect_uri=settings.m365_redirect_uri,
                    read_only=settings.m365_read_only,
                )
            )
            for mailbox in settings.m365_monitored_mailbox_list:
                try:
                    raw = await client.list_messages(mailbox=mailbox, limit=50)
                    messages.extend(raw or [])
                except Exception:
                    continue
        elif settings.m365_operative_demo_mode:
            demo = True
            messages = demo_inbox_messages()
        else:
            return M365SyncResponse(
                ingested=0,
                processed=0,
                skipped=0,
                graph_connected=False,
                demo_mode=False,
                message="Conecta tu buzón con correo y contraseña en Cuentas M365.",
            )

        for msg in messages:
            ingested += 1
            created = await self._process_raw_message(
                msg,
                graph_connected=using_imap or using_graph,
                demo_source=demo,
            )
            if created:
                processed += 1
            else:
                skipped += 1
        await self.db.commit()
        source = "IMAP" if using_imap else ("Graph" if using_graph else "demo")
        return M365SyncResponse(
            ingested=ingested,
            processed=processed,
            skipped=skipped,
            graph_connected=using_imap or using_graph,
            demo_mode=demo,
            message=f"Bandeja sincronizada ({source})",
        )

    async def ingest_webhook(self, payload: M365InboundEmailWebhook) -> M365ProcessedEmailResponse:
        msg = {
            "external_message_id": payload.message_id or f"webhook-{uuid.uuid4()}",
            "mailbox": payload.mailbox,
            "subject": payload.subject,
            "sender_email": payload.sender_email,
            "sender_name": payload.sender_name,
            "received_at": payload.received_at or datetime.now(timezone.utc),
            "body_text": payload.body_text,
            "attachments": [a.model_dump() for a in payload.attachments],
        }
        row = await self._process_raw_message(
            msg,
            graph_connected=(await self.mailbox_connected()) or self._graph_api_configured(),
            demo_source=False,
        )
        if row is None:
            existing = await self._get_by_external(msg["external_message_id"])
            row = existing
        await self.db.commit()
        return self._to_response(row)  # type: ignore[arg-type]

    async def _process_raw_message(
        self,
        msg: dict,
        *,
        graph_connected: bool,
        demo_source: bool,
    ) -> M365ProcessedEmail | None:
        external_id = str(msg.get("external_message_id") or msg.get("id") or uuid.uuid4())
        existing = await self._get_by_external(external_id)
        if existing:
            return None
        subject = str(msg.get("subject") or "(sin asunto)")
        body = str(msg.get("body_text") or msg.get("body_preview") or "")
        sender_email = str(msg.get("sender_email") or msg.get("from") or "unknown@unknown")
        sender_name = msg.get("sender_name")
        attachments_raw = list(msg.get("attachments") or [])
        classification = self._classifier.classify(
            subject=subject,
            body=body,
            sender_email=sender_email,
            attachment_names=[a.get("name", "") for a in attachments_raw],
        )
        attachment_texts = [
            (str(a.get("name", "adjunto")), str(a.get("extracted_text") or a.get("name", "")))
            for a in attachments_raw
        ]
        extracted = self._extractor.extract(
            subject=subject,
            body=body,
            sender_email=sender_email,
            sender_name=sender_name,
            attachment_texts=attachment_texts,
        )
        relations = await self._relations.relate(
            subject=subject,
            body=body,
            extracted=extracted,
            classification=classification.classification,
        )
        dgcp_id = None
        for rel in relations:
            if rel.entity_type == "dgcp_opportunity" and rel.entity_id:
                dgcp_id = uuid.UUID(rel.entity_id)
                break
        amount = extracted.get("amount")
        currency = extracted.get("currency")
        primary_attachment = attachments_raw[0]["name"] if attachments_raw else f"{classification.classification}.eml"
        sharepoint_path = self._sharepoint.build_path(
            classification=classification.classification,
            vendor=extracted.get("vendor"),
            client=extracted.get("client"),
            dgcp_code=extracted.get("dgcp_process_code"),
            filename=str(primary_attachment),
        )
        suggested = self._build_suggested_actions(
            classification=classification.classification,
            extracted=extracted,
            relations=relations,
            confidence=classification.confidence,
        )
        received = msg.get("received_at")
        if isinstance(received, str):
            received = datetime.fromisoformat(received.replace("Z", "+00:00"))
        if not isinstance(received, datetime):
            received = datetime.now(timezone.utc)
        row = M365ProcessedEmail(
            tenant_id=self.tenant_id,
            mailbox=str(msg.get("mailbox") or settings.m365_monitored_mailbox_list[0]),
            external_message_id=external_id,
            subject=subject,
            sender_email=sender_email,
            sender_name=sender_name,
            received_at=received,
            body_preview=body[:500],
            body_text=body,
            classification=classification.classification,
            classification_confidence=classification.confidence,
            extracted_data=extracted,
            relations={"items": [r.model_dump() for r in relations]},
            suggested_actions=[a.model_dump() for a in suggested],
            attachments=attachments_raw,
            sharepoint_path=sharepoint_path,
            graph_connected=graph_connected,
            demo_source=demo_source,
            hermes_indexed=True,
            related_dgcp_process_id=dgcp_id,
            amount=Decimal(str(amount)) if amount is not None else None,
            currency=currency,
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit.log(
            action="m365.email_processed",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="m365_email",
            resource_id=row.id,
            details={"classification": classification.classification, "subject": subject[:120]},
        )
        self.db.add(
            M365AutomationEvent(
                tenant_id=self.tenant_id,
                event_type="email_processed",
                source="m365_operative",
                payload={"email_id": str(row.id), "classification": classification.classification},
                status="completed",
            )
        )
        return row

    async def _get_by_external(self, external_id: str) -> M365ProcessedEmail | None:
        result = await self.db.execute(
            select(M365ProcessedEmail).where(
                M365ProcessedEmail.tenant_id == self.tenant_id,
                M365ProcessedEmail.external_message_id == external_id,
            )
        )
        return result.scalar_one_or_none()

    def _build_suggested_actions(
        self,
        *,
        classification: str,
        extracted: dict,
        relations: list,
        confidence: int,
    ) -> list[M365SuggestedAction]:
        actions: list[M365SuggestedAction] = []
        has_dgcp = any(r.entity_type == "dgcp_opportunity" for r in relations)

        def add(key: str, extra_conf: int = 0, href: str | None = None) -> None:
            label, desc = ACTION_CATALOG[key]
            actions.append(
                M365SuggestedAction(
                    key=key,
                    label=label,
                    description=desc,
                    confidence=min(98, confidence + extra_conf),
                    href=href,
                    auto_eligible=key in ("archive_sharepoint", "notify_teams"),
                )
            )

        if classification in ("cotizacion_proveedor", "catalogo", "ficha_tecnica"):
            add("save_as_quote", 4, "/prices")
            add("archive_sharepoint", 2)
            if has_dgcp:
                add("attach_to_process", 8, "/dgcp")
                add("create_economic_offer", 6, "/dgcp")
                add("save_to_expediente", 5, "/dgcp/expedientes")
            add("create_task", 3, "/tasks")
            add("notify_teams", 1)
        elif classification == "licitacion":
            add("attach_to_process", 10, "/dgcp")
            add("save_to_expediente", 8, "/dgcp/expedientes")
            add("create_task", 6, "/tasks")
            add("archive_sharepoint", 4)
            add("notify_teams", 5)
        elif classification == "orden_compra":
            add("create_task", 8, "/tasks")
            add("notify_teams", 4)
            add("archive_sharepoint", 3, "/odoo")
        elif classification == "factura_proveedor":
            add("send_to_cxp", 8, "/odoo")
            add("archive_sharepoint", 4)
            add("create_task", 3, "/tasks")
        elif classification in ("factura_cliente", "comprobante_pago"):
            add("notify_cxc", 8, "/odoo")
            add("archive_sharepoint", 3)
        else:
            add("archive_sharepoint", 0)
            add("create_task", 0, "/tasks")
        return actions[:6]

    async def get_dashboard(self) -> M365OperativeDashboard:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        total_today = await self.db.scalar(
            select(func.count()).select_from(M365ProcessedEmail).where(
                M365ProcessedEmail.tenant_id == self.tenant_id,
                M365ProcessedEmail.received_at >= today_start,
            )
        )
        emails = await self.db.execute(
            select(M365ProcessedEmail)
            .where(M365ProcessedEmail.tenant_id == self.tenant_id)
            .order_by(M365ProcessedEmail.received_at.desc())
            .limit(8)
        )
        recent = list(emails.scalars().all())
        all_rows = await self.db.execute(
            select(M365ProcessedEmail).where(M365ProcessedEmail.tenant_id == self.tenant_id)
        )
        rows = list(all_rows.scalars().all())
        mailboxes = await self.db.scalar(
            select(func.count()).select_from(M365MonitoredMailbox).where(
                M365MonitoredMailbox.tenant_id == self.tenant_id,
                M365MonitoredMailbox.is_active.is_(True),
            )
        )
        tasks_generated = await self.db.scalar(
            select(func.count()).select_from(M365EmailActionLog).where(
                M365EmailActionLog.tenant_id == self.tenant_id,
                M365EmailActionLog.action_key == "create_task",
            )
        )
        counts = self._classification_counts(rows)
        briefing = self._briefing_lines(counts, len(rows))
        quick = [
            M365SuggestedAction(key="view_emails", label="Ver correos importantes", href="/m365/operativo"),
            M365SuggestedAction(key="attach_docs", label="Adjuntar documentos", href="/m365/operativo"),
            M365SuggestedAction(key="create_offers", label="Crear ofertas", href="/dgcp"),
            M365SuggestedAction(key="view_bids", label="Ver licitaciones", href="/dgcp"),
        ]
        real, demo = await self._mail_source_flags()
        return M365OperativeDashboard(
            graph_connected=real,
            demo_mode=demo,
            mailboxes_monitored=int(mailboxes or 0),
            emails_today=int(total_today or 0),
            attachments_processed=sum(len(r.attachments or []) for r in rows if r.received_at >= today_start),
            quotes_detected=counts.get("cotizacion_proveedor", 0),
            invoices_detected=counts.get("factura_proveedor", 0) + counts.get("factura_cliente", 0),
            purchase_orders_detected=counts.get("orden_compra", 0),
            dgcp_documents_detected=counts.get("licitacion", 0),
            tasks_generated=int(tasks_generated or 0),
            documents_indexed=sum(1 for r in rows if r.hermes_indexed),
            pending_actions=sum(len(r.suggested_actions or []) for r in rows),
            recent_emails=[self._to_response(r) for r in recent],
            briefing_lines=briefing,
            quick_actions=quick,
        )

    @staticmethod
    def _classification_counts(rows: list[M365ProcessedEmail]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            counts[row.classification] = counts.get(row.classification, 0) + 1
        return counts

    @staticmethod
    def _briefing_lines(counts: dict[str, int], total: int) -> list[str]:
        if total == 0:
            return ["Sin correos procesados. Conecta tu buzón o ejecuta sincronización."]
        lines = [f"Recibimos {total} correo(s) procesados."]
        mapping = [
            ("cotizacion_proveedor", "cotización(es) proveedor"),
            ("orden_compra", "orden(es) de compra"),
            ("factura_proveedor", "factura(s) proveedor"),
            ("licitacion", "documento(s) DGCP"),
        ]
        bullets = []
        for key, label in mapping:
            if counts.get(key):
                bullets.append(f"• {counts[key]} {label}")
        if counts.get("licitacion", 0) == 0 and counts.get("cotizacion_proveedor", 0):
            bullets.append("• Oportunidades comerciales detectadas en cotizaciones")
        return lines + bullets

    async def list_emails(
        self,
        *,
        classification: str | None = None,
        limit: int = 50,
    ) -> M365ProcessedEmailListResponse:
        query = (
            select(M365ProcessedEmail)
            .where(M365ProcessedEmail.tenant_id == self.tenant_id)
            .order_by(M365ProcessedEmail.received_at.desc())
            .limit(limit)
        )
        if classification:
            query = query.where(M365ProcessedEmail.classification == classification)
        result = await self.db.execute(query)
        items = [self._to_response(r) for r in result.scalars().all()]
        total = await self.db.scalar(
            select(func.count()).select_from(M365ProcessedEmail).where(
                M365ProcessedEmail.tenant_id == self.tenant_id
            )
        )
        real, demo = await self._mail_source_flags()
        return M365ProcessedEmailListResponse(
            items=items,
            total=int(total or 0),
            graph_connected=real,
            demo_mode=demo,
            message="Modo demo activo" if demo else None,
        )

    async def get_email(self, email_id: uuid.UUID) -> M365ProcessedEmailResponse | None:
        row = await self.db.get(M365ProcessedEmail, email_id)
        if not row or row.tenant_id != self.tenant_id:
            return None
        return self._to_response(row)

    async def execute_action(
        self,
        email_id: uuid.UUID,
        action_key: str,
        *,
        user: User,
        params: dict | None = None,
    ) -> M365ExecuteActionResponse:
        row = await self.db.get(M365ProcessedEmail, email_id)
        if not row or row.tenant_id != self.tenant_id:
            return M365ExecuteActionResponse(status="error", action_key=action_key, message="Correo no encontrado")
        params = params or {}
        extracted = row.extracted_data or {}
        label = ACTION_CATALOG.get(action_key, (action_key, ""))[0]
        result: dict = {}
        task_id = None
        notification_id = None

        if action_key == "create_task":
            task_svc = TaskService(self.db, self.tenant_id, user_id=user.id)
            event_type = {
                "cotizacion_proveedor": "supplier_quote_received",
                "licitacion": "dgcp_document_received",
                "orden_compra": "customer_po_received",
                "factura_proveedor": "vendor_invoice_received",
            }.get(row.classification, "m365_email_received")
            task = await task_svc.create_from_event(
                TaskFromEventRequest(
                    source="m365",
                    event_type=event_type,
                    title=f"M365: {row.subject[:120]}",
                    description=row.body_preview,
                    customer_name=extracted.get("client"),
                    amount=row.amount,
                    currency=row.currency or "USD",
                    dgcp_process_id=row.related_dgcp_process_id,
                    related_entity_type="m365_email",
                    related_entity_id=str(row.id),
                    metadata={"email_id": str(row.id), "classification": row.classification, **params},
                )
            )
            task_id = task.id
            row.related_task_id = task.id
            result = {"task_id": str(task.id), "title": task.title}
        elif action_key == "create_economic_offer" and row.related_dgcp_process_id:
            draft = EconomicOfferDraft(
                tenant_id=self.tenant_id,
                opportunity_id=row.related_dgcp_process_id,
                user_id=user.id,
                customer_name=extracted.get("client"),
                suggested_products=extracted.get("products") or [],
                estimated_amount=row.amount,
                currency=row.currency or "USD",
                notes=f"Generado desde correo: {row.subject}",
                metadata_={"email_id": str(row.id), "vendor": extracted.get("vendor")},
            )
            self.db.add(draft)
            await self.db.flush()
            result = {"draft_id": str(draft.id), "opportunity_id": str(row.related_dgcp_process_id)}
        elif action_key == "archive_sharepoint":
            meta = self._sharepoint.archive_metadata(
                classification=row.classification,
                sharepoint_path=row.sharepoint_path or "",
                extracted=extracted,
            )
            row.hermes_indexed = True
            result = meta
        elif action_key in ("attach_to_process", "save_to_expediente"):
            result = {
                "dgcp_process_id": str(row.related_dgcp_process_id) if row.related_dgcp_process_id else None,
                "expediente_path": row.sharepoint_path,
                "attached": True,
            }
        elif action_key == "notify_teams":
            teams = M365TeamsNotificationService(self.db, self.tenant_id, user.id)
            vendor = extracted.get("vendor") or row.sender_name or "Remitente"
            dgcp = extracted.get("dgcp_process_code") or "proceso activo"
            msg = f"{vendor} envió {self._classifier.label(row.classification).lower()} para {dgcp}"
            notification_id = await teams.notify_email_processed(
                user_id=user.id,
                title="Microsoft 365 — nuevo correo procesado",
                message=msg,
                email_id=row.id,
            )
            result = {"teams_notified": True, "message": msg}
        elif action_key == "send_to_cxp":
            result = {"routed_to": "accounts_payable", "vendor": extracted.get("vendor"), "amount": extracted.get("amount")}
        elif action_key == "notify_cxc":
            notif_svc = NotificationService(self.db, self.tenant_id, user.id)
            notif = await notif_svc.create(
                user_id=user.id,
                title="CxC — comprobante recibido",
                message=f"Cliente {extracted.get('client') or 'N/D'} — revisar conciliación",
                type="m365_cxc",
                severity="info",
                related_entity_type="m365_email",
                related_entity_id=str(row.id),
            )
            notification_id = notif.id
            result = {"cxc_notified": True}
        elif action_key == "save_as_quote":
            result = {"saved_as": "supplier_quote", "vendor": extracted.get("vendor"), "href": "/prices"}
        else:
            return M365ExecuteActionResponse(status="error", action_key=action_key, message="Acción no soportada")

        self.db.add(
            M365EmailActionLog(
                tenant_id=self.tenant_id,
                email_id=row.id,
                user_id=user.id,
                action_key=action_key,
                action_label=label,
                status="completed",
                result=result,
            )
        )
        await self.db.commit()
        return M365ExecuteActionResponse(
            status="ok",
            action_key=action_key,
            message=f"Acción «{label}» ejecutada",
            result=result,
            task_id=task_id,
            notification_id=notification_id,
        )

    async def calendar_suggestions(self) -> M365CalendarSuggestionsResponse:
        result = await self.db.execute(
            select(M365ProcessedEmail)
            .where(M365ProcessedEmail.tenant_id == self.tenant_id)
            .order_by(M365ProcessedEmail.received_at.desc())
            .limit(20)
        )
        return self._calendar.list_for_emails(list(result.scalars().all()))

    def _to_response(self, row: M365ProcessedEmail) -> M365ProcessedEmailResponse:
        rel_items = row.relations.get("items", []) if isinstance(row.relations, dict) else []
        from app.schemas.m365_operative import M365EmailRelation

        relations = [M365EmailRelation(**item) for item in rel_items]
        actions = [M365SuggestedAction(**a) for a in (row.suggested_actions or [])]
        attachments = row.attachments or []
        return M365ProcessedEmailResponse(
            id=row.id,
            mailbox=row.mailbox,
            external_message_id=row.external_message_id,
            subject=row.subject,
            sender_email=row.sender_email,
            sender_name=row.sender_name,
            received_at=row.received_at,
            body_preview=row.body_preview,
            classification=row.classification,
            classification_label=self._classifier.label(row.classification),
            classification_confidence=row.classification_confidence,
            extracted_data=row.extracted_data or {},
            relations=relations,
            suggested_actions=actions,
            attachments=attachments,
            sharepoint_path=row.sharepoint_path,
            processing_status=row.processing_status,
            graph_connected=row.graph_connected,
            demo_source=row.demo_source,
            hermes_indexed=row.hermes_indexed,
            related_dgcp_process_id=row.related_dgcp_process_id,
            related_task_id=row.related_task_id,
            amount=row.amount,
            currency=row.currency,
        )

    async def get_briefing_stats(self) -> dict:
        dashboard = await self.get_dashboard()
        total = await self.db.scalar(
            select(func.count()).select_from(M365ProcessedEmail).where(
                M365ProcessedEmail.tenant_id == self.tenant_id
            )
        )
        return {
            "total_emails": int(total or 0),
            "quotes": dashboard.quotes_detected,
            "purchase_orders": dashboard.purchase_orders_detected,
            "vendor_invoices": dashboard.invoices_detected,
            "dgcp_docs": dashboard.dgcp_documents_detected,
            "lines": dashboard.briefing_lines,
        }
