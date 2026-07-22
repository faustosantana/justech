"""Estado agregado del Communications Hub."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.m365_account import M365UserAccount
from app.models.whatsapp import WhatsappSession
from app.schemas.communications import ChannelStatus, CommunicationsHubStatus
from integrations.whatsapp.bridge_client import WhatsAppBridgeClient


class CommunicationsHubService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def get_status(self) -> CommunicationsHubStatus:
        m365_q = await self.db.execute(
            select(M365UserAccount).where(
                M365UserAccount.tenant_id == self.tenant_id,
                M365UserAccount.jaios_user_id == self.user_id,
                M365UserAccount.is_active.is_(True),
            )
        )
        m365 = m365_q.scalar_one_or_none()
        outlook_status = "connected" if m365 and m365.connection_status == "connected" else "not_connected"
        outlook_detail = m365.email if m365 else None

        wa_count_q = await self.db.execute(
            select(func.count())
            .select_from(WhatsappSession)
            .where(
                WhatsappSession.tenant_id == self.tenant_id,
                WhatsappSession.user_id == self.user_id,
                WhatsappSession.is_active.is_(True),
                WhatsappSession.connection_status == "connected",
            )
        )
        wa_connected = int(wa_count_q.scalar() or 0)
        wa_total_q = await self.db.execute(
            select(func.count())
            .select_from(WhatsappSession)
            .where(
                WhatsappSession.tenant_id == self.tenant_id,
                WhatsappSession.user_id == self.user_id,
                WhatsappSession.is_active.is_(True),
            )
        )
        wa_total = int(wa_total_q.scalar() or 0)

        bridge_ok = False
        try:
            await WhatsAppBridgeClient().health()
            bridge_ok = True
        except Exception:
            bridge_ok = False

        if wa_connected > 0:
            wa_status, wa_detail = "connected", f"{wa_connected} cuenta(s) activa(s)"
        elif wa_total > 0:
            wa_status, wa_detail = "pending", f"{wa_total} cuenta(s) — esperando conexión"
        elif bridge_ok:
            wa_status, wa_detail = "ready", "Bridge listo — conecta tu WhatsApp"
        else:
            wa_status, wa_detail = "unavailable", "Bridge no disponible en desarrollo"

        return CommunicationsHubStatus(
            outlook=ChannelStatus(
                channel="outlook",
                label="Outlook",
                status=outlook_status,
                detail=outlook_detail,
                route="/comunicaciones?tab=outlook",
            ),
            whatsapp=ChannelStatus(
                channel="whatsapp",
                label="WhatsApp",
                status=wa_status,
                detail=wa_detail,
                route="/comunicaciones?tab=whatsapp",
            ),
            teams=ChannelStatus(
                channel="teams",
                label="Teams",
                status=outlook_status if m365 else "not_connected",
                detail="Incluido en Microsoft 365",
                route="/comunicaciones?tab=teams",
            ),
            contacts=ChannelStatus(
                channel="contacts",
                label="Contactos",
                status="active",
                detail="Perfil 360 — Outlook, WhatsApp, Odoo, Teams, DGCP",
                route="/comunicaciones?tab=contactos",
            ),
            search=ChannelStatus(
                channel="search",
                label="Búsqueda",
                status="active",
                detail="WhatsApp + Outlook + Teams + repositorios M365/JAIOS",
                route="/comunicaciones?tab=historial",
            ),
            ai=ChannelStatus(
                channel="ai",
                label="IA",
                status="active",
                detail="Clasificación automática + 10 acciones en WhatsApp",
                route="/comunicaciones?tab=ia",
            ),
        )
