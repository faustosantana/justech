"""Búsqueda unificada Communications Hub — Fase 3."""

from __future__ import annotations

import re
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.whatsapp import WhatsappChat, WhatsappMessage, WhatsappSession
from app.schemas.communications import CommunicationsTimelineItem, CommunicationsUnifiedSearchResponse
from app.schemas.search import SearchResultGroup, SearchResultItem
from app.services.enterprise_search_service import EnterpriseSearchService, GROUP_LABELS
from app.services.m365_connection_service import M365ConnectionService
from app.services.m365_service import M365Service
from integrations.microsoft365.errors import GraphError

COMMUNICATIONS_GROUP_LABELS: dict[str, str] = {
    "whatsapp_chats": "WhatsApp — conversaciones",
    "whatsapp_messages": "WhatsApp — mensajes",
    "outlook_mail": "Outlook — correos",
    "teams": "Microsoft Teams",
    "m365_files": "OneDrive / SharePoint",
    **GROUP_LABELS,
}


class CommunicationsSearchService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._enterprise = EnterpriseSearchService(db, tenant_id, user_id)

    @staticmethod
    def _tokens(query: str) -> list[str]:
        return [t for t in re.split(r"[^a-z0-9áéíóúñ]+", query.lower()) if len(t) >= 2]

    @staticmethod
    def _score(query: str, *texts: str | None) -> float:
        q = query.lower().strip()
        tokens = CommunicationsSearchService._tokens(q)
        best = 0.0
        for raw in texts:
            if not raw:
                continue
            t = raw.lower()
            if t == q:
                best = max(best, 100.0)
            elif q in t:
                best = max(best, 85.0)
            elif tokens and all(tok in t for tok in tokens):
                best = max(best, 75.0)
            elif tokens and any(tok in t for tok in tokens):
                best = max(best, 55.0)
        return best or 40.0

    def _item(
        self,
        *,
        id_: str,
        type_: str,
        title: str,
        subtitle: str | None,
        description: str | None,
        source: str,
        url: str,
        query: str,
        company: str | None = None,
        metadata: dict | None = None,
    ) -> SearchResultItem:
        return SearchResultItem(
            id=id_,
            type=type_,
            title=title,
            subtitle=subtitle,
            description=description,
            source=source,
            url=url,
            company=company,
            score=self._score(query, title, subtitle, description),
            metadata=metadata or {},
        )

    async def unified_search(
        self,
        query: str,
        *,
        channel_filter: str | None = None,
        limit_per_group: int = 8,
    ) -> CommunicationsUnifiedSearchResponse:
        q = query.strip()
        if len(q) < 2:
            return CommunicationsUnifiedSearchResponse(query=q, total=0, groups=[], timeline=[], sources_searched=[])

        start = time.perf_counter()
        groups: list[SearchResultGroup] = []
        sources: list[str] = []
        timeline: list[CommunicationsTimelineItem] = []

        if channel_filter in (None, "whatsapp"):
            wa_groups, wa_timeline = await self._search_whatsapp(q, limit_per_group)
            if wa_groups:
                groups.extend(wa_groups)
                sources.append("whatsapp")
            timeline.extend(wa_timeline)

        if channel_filter in (None, "outlook", "teams", "m365"):
            m365_groups, m365_timeline = await self._search_m365(q, limit_per_group, channel_filter=channel_filter)
            if m365_groups:
                groups.extend(m365_groups)
                sources.append("m365")
            timeline.extend(m365_timeline)

        if channel_filter in (None, "enterprise", "documents", "odoo", "dgcp"):
            ent = await self._enterprise.search(q, limit_per_group=limit_per_group, channel="comms_hub")
            for group in ent.groups:
                if channel_filter == "documents" and group.type not in ("documents", "knowledge"):
                    continue
                if channel_filter == "odoo" and group.type not in (
                    "customers", "products", "invoices", "quotations", "opportunities", "vendors", "projects",
                ):
                    continue
                if channel_filter == "dgcp" and group.type != "dgcp":
                    continue
                groups.append(group)
            for src in ent.sources_searched:
                if src not in sources:
                    sources.append(src)

        groups = self._merge_groups(groups)
        groups.sort(key=lambda g: max((i.score for i in g.items), default=0), reverse=True)
        timeline.sort(key=lambda t: t.timestamp or datetime.min.replace(tzinfo=UTC), reverse=True)
        timeline = timeline[:30]

        total = sum(g.count for g in groups)
        latency = int((time.perf_counter() - start) * 1000)

        return CommunicationsUnifiedSearchResponse(
            query=q,
            total=total,
            groups=groups,
            timeline=timeline,
            sources_searched=list(dict.fromkeys(sources)),
            latency_ms=latency,
        )

    async def _search_whatsapp(
        self, query: str, limit: int
    ) -> tuple[list[SearchResultGroup], list[CommunicationsTimelineItem]]:
        tokens = self._tokens(query)
        term = f"%{query}%"

        session_q = await self.db.execute(
            select(WhatsappSession.id).where(
                WhatsappSession.tenant_id == self.tenant_id,
                WhatsappSession.user_id == self.user_id,
                WhatsappSession.is_active.is_(True),
            )
        )
        session_ids = [row[0] for row in session_q.all()]
        if not session_ids:
            return [], []

        chat_stmt = select(WhatsappChat).where(
            WhatsappChat.tenant_id == self.tenant_id,
            WhatsappChat.session_id.in_(session_ids),
        )
        if tokens:
            for tok in tokens:
                t = f"%{tok}%"
                chat_stmt = chat_stmt.where(
                    or_(
                        WhatsappChat.name.ilike(t),
                        WhatsappChat.last_message_preview.ilike(t),
                        WhatsappChat.remote_jid.ilike(t),
                    )
                )
        else:
            chat_stmt = chat_stmt.where(
                or_(
                    WhatsappChat.name.ilike(term),
                    WhatsappChat.last_message_preview.ilike(term),
                    WhatsappChat.remote_jid.ilike(term),
                )
            )
        chat_rows = (await self.db.execute(chat_stmt.limit(limit))).scalars().all()

        msg_stmt = (
            select(WhatsappMessage)
            .where(
                WhatsappMessage.tenant_id == self.tenant_id,
                WhatsappMessage.session_id.in_(session_ids),
            )
        )
        if tokens:
            for tok in tokens:
                msg_stmt = msg_stmt.where(WhatsappMessage.body.ilike(f"%{tok}%"))
        else:
            msg_stmt = msg_stmt.where(WhatsappMessage.body.ilike(term))
        msg_rows = (await self.db.execute(msg_stmt.order_by(WhatsappMessage.wa_timestamp_ms.desc()).limit(limit))).scalars().all()

        chat_items: list[SearchResultItem] = []
        timeline: list[CommunicationsTimelineItem] = []

        for chat in chat_rows:
            title = chat.name or chat.remote_jid.split("@")[0]
            item = self._item(
                id_=str(chat.id),
                type_="whatsapp_chats",
                title=title,
                subtitle=chat.last_message_preview,
                description=chat.ai_classification.get("intent_summary") if chat.ai_classification else None,
                source="whatsapp",
                url=f"/comunicaciones?tab=whatsapp&chat={chat.id}",
                query=query,
                metadata={
                    "session_id": str(chat.session_id),
                    "remote_jid": chat.remote_jid,
                    "classification": chat.ai_classification.get("classification") if chat.ai_classification else None,
                },
            )
            chat_items.append(item)
            if chat.last_message_at:
                timeline.append(
                    CommunicationsTimelineItem(
                        id=str(chat.id),
                        channel="whatsapp",
                        title=title,
                        subtitle="Conversación",
                        preview=chat.last_message_preview,
                        timestamp=chat.last_message_at,
                        url=item.url,
                        score=item.score,
                    )
                )

        msg_items: list[SearchResultItem] = []
        for msg in msg_rows:
            preview = (msg.body or "")[:160]
            item = self._item(
                id_=str(msg.id),
                type_="whatsapp_messages",
                title=preview[:80] or "[media]",
                subtitle=msg.remote_jid.split("@")[0],
                description=preview,
                source="whatsapp",
                url=f"/comunicaciones?tab=whatsapp&chat={msg.chat_id}" if msg.chat_id else "/comunicaciones?tab=whatsapp",
                query=query,
                metadata={"from_me": msg.from_me, "remote_jid": msg.remote_jid},
            )
            msg_items.append(item)
            ts = None
            if msg.wa_timestamp_ms:
                ts = datetime.fromtimestamp(msg.wa_timestamp_ms / 1000, tz=UTC)
            timeline.append(
                CommunicationsTimelineItem(
                    id=str(msg.id),
                    channel="whatsapp",
                    title=preview[:80] or "Mensaje WhatsApp",
                    subtitle="Mensaje" + (" (enviado)" if msg.from_me else " (recibido)"),
                    preview=preview,
                    timestamp=ts or msg.created_at,
                    url=item.url,
                    score=item.score,
                )
            )

        groups: list[SearchResultGroup] = []
        if chat_items:
            chat_items.sort(key=lambda x: x.score, reverse=True)
            groups.append(
                SearchResultGroup(
                    type="whatsapp_chats",
                    label=COMMUNICATIONS_GROUP_LABELS["whatsapp_chats"],
                    count=len(chat_items),
                    items=chat_items,
                )
            )
        if msg_items:
            msg_items.sort(key=lambda x: x.score, reverse=True)
            groups.append(
                SearchResultGroup(
                    type="whatsapp_messages",
                    label=COMMUNICATIONS_GROUP_LABELS["whatsapp_messages"],
                    count=len(msg_items),
                    items=msg_items,
                )
            )
        return groups, timeline

    async def _search_m365(
        self, query: str, limit: int, *, channel_filter: str | None
    ) -> tuple[list[SearchResultGroup], list[CommunicationsTimelineItem]]:
        conn = await M365ConnectionService(self.db, self.tenant_id, self.user_id).connection_state()
        if not conn.account_connected:
            return [], []

        groups: list[SearchResultGroup] = []
        timeline: list[CommunicationsTimelineItem] = []

        try:
            m365 = await M365Service(self.db, self.tenant_id, user_id=self.user_id).search(query, limit=limit)
        except GraphError:
            return [], []

        mail_items: list[SearchResultItem] = []
        for hit in m365.hits:
            if hit.get("type") != "mail":
                continue
            subject = hit.get("subject") or "(sin asunto)"
            sender = hit.get("sender_name") or hit.get("sender") or ""
            preview = hit.get("preview") or ""
            received = hit.get("received_at")
            item = self._item(
                id_=hit.get("id") or subject,
                type_="outlook_mail",
                title=subject,
                subtitle=sender,
                description=preview[:200],
                source="m365",
                url="/comunicaciones?tab=outlook",
                query=query,
                metadata={"message_id": hit.get("id")},
            )
            mail_items.append(item)
            ts = None
            if received:
                try:
                    ts = datetime.fromisoformat(str(received).replace("Z", "+00:00"))
                except ValueError:
                    ts = None
            timeline.append(
                CommunicationsTimelineItem(
                    id=str(hit.get("id") or subject),
                    channel="outlook",
                    title=subject,
                    subtitle=sender,
                    preview=preview[:160],
                    timestamp=ts,
                    url=item.url,
                    score=item.score,
                )
            )

        if mail_items and channel_filter in (None, "outlook", "m365"):
            groups.append(
                SearchResultGroup(
                    type="outlook_mail",
                    label=COMMUNICATIONS_GROUP_LABELS["outlook_mail"],
                    count=len(mail_items),
                    items=mail_items[:limit],
                )
            )

        team_items: list[SearchResultItem] = []
        for hit in m365.hits:
            if hit.get("type") != "teams":
                continue
            name = hit.get("display_name") or hit.get("name") or "Equipo Teams"
            item = self._item(
                id_=hit.get("id") or name,
                type_="teams",
                title=name,
                subtitle=hit.get("description"),
                description=None,
                source="m365",
                url="/comunicaciones?tab=teams",
                query=query,
            )
            team_items.append(item)
            timeline.append(
                CommunicationsTimelineItem(
                    id=str(hit.get("id") or name),
                    channel="teams",
                    title=name,
                    subtitle="Equipo Microsoft Teams",
                    preview=hit.get("description"),
                    timestamp=None,
                    url=item.url,
                    score=item.score,
                )
            )

        if team_items and channel_filter in (None, "teams", "m365"):
            groups.append(
                SearchResultGroup(
                    type="teams",
                    label=COMMUNICATIONS_GROUP_LABELS["teams"],
                    count=len(team_items),
                    items=team_items[:limit],
                )
            )

        file_items: list[SearchResultItem] = []
        for hit in m365.hits:
            if hit.get("type") not in ("onedrive", "sharepoint"):
                continue
            name = hit.get("name") or "Archivo"
            item = self._item(
                id_=hit.get("id") or name,
                type_="m365_files",
                title=name,
                subtitle=hit.get("type"),
                description=None,
                source="m365",
                url="/comunicaciones?tab=outlook",
                query=query,
            )
            file_items.append(item)

        if file_items and channel_filter in (None, "m365", "documents"):
            groups.append(
                SearchResultGroup(
                    type="m365_files",
                    label=COMMUNICATIONS_GROUP_LABELS["m365_files"],
                    count=len(file_items),
                    items=file_items[:limit],
                )
            )

        return groups, timeline

    @staticmethod
    def _merge_groups(groups: list[SearchResultGroup]) -> list[SearchResultGroup]:
        by_type: dict[str, SearchResultGroup] = {}
        for group in groups:
            if group.type not in by_type:
                by_type[group.type] = group
            else:
                existing = by_type[group.type]
                seen = {i.id for i in existing.items}
                merged = list(existing.items)
                for item in group.items:
                    if item.id not in seen:
                        merged.append(item)
                        seen.add(item.id)
                merged.sort(key=lambda x: x.score, reverse=True)
                by_type[group.type] = SearchResultGroup(
                    type=group.type,
                    label=existing.label,
                    count=len(merged),
                    items=merged,
                )
        return list(by_type.values())
