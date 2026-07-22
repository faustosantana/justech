"""Contactos unificados 360 — Outlook, WhatsApp, Odoo, Teams, DGCP."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.task import Task
from app.models.unified_contact import UnifiedContact, UnifiedContactIdentity
from app.models.whatsapp import WhatsappChat, WhatsappSession
from app.schemas.communications import (
    UnifiedContactIdentityResponse,
    UnifiedContactListResponse,
    UnifiedContactProfile360,
    UnifiedContactResponse,
    UnifiedContactStats,
    UnifiedContactSyncResponse,
)
from app.services.communications_search_service import CommunicationsSearchService
from app.services.entity_resolution_engine import _normalize
from app.services.m365_connection_service import M365ConnectionService
from app.services.m365_service import M365Service
from app.services.odoo_detail_service import OdooDetailService
from app.services.odoo_service import OdooService
from integrations.microsoft365.errors import GraphError


@dataclass
class _IdentitySeed:
    source: str
    external_id: str
    display_name: str
    email: str | None = None
    phone: str | None = None
    company_name: str | None = None
    profile_url: str | None = None
    extra: dict | None = None


class UnifiedContactService:
    SOURCE_LABELS = {
        "outlook": "Outlook",
        "whatsapp": "WhatsApp",
        "odoo": "Odoo",
        "teams": "Teams",
        "dgcp": "DGCP",
    }

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    @staticmethod
    def _normalize_phone(phone: str | None) -> str | None:
        if not phone:
            return None
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 8:
            return None
        return digits[-10:] if len(digits) >= 10 else digits

    @staticmethod
    def _phone_from_jid(jid: str) -> str | None:
        if not jid:
            return None
        return UnifiedContactService._normalize_phone(jid.split("@")[0])

    @classmethod
    def _match_key(
        cls,
        *,
        email: str | None = None,
        phone: str | None = None,
        name: str | None = None,
        company: str | None = None,
    ) -> str:
        if email and email.strip():
            return f"email:{email.strip().lower()}"
        norm_phone = cls._normalize_phone(phone)
        if norm_phone:
            return f"phone:{norm_phone}"
        n = _normalize(name or "")
        c = _normalize(company or "")
        if c and n:
            return f"org:{c}|{n}"
        if n:
            return f"name:{n}"
        return f"unknown:{uuid.uuid4().hex[:12]}"

    async def sync_contacts(self, *, limit_per_source: int = 80) -> UnifiedContactSyncResponse:
        seeds = await self._collect_seeds(limit_per_source)
        merged: dict[str, list[_IdentitySeed]] = {}
        for seed in seeds:
            key = self._match_key(
                email=seed.email,
                phone=seed.phone,
                name=seed.display_name,
                company=seed.company_name,
            )
            merged.setdefault(key, []).append(seed)

        created = updated = 0
        now = datetime.now(UTC)

        for key, group in merged.items():
            primary = group[0]
            for alt in group[1:]:
                if not primary.email and alt.email:
                    primary = alt
                if not primary.phone and alt.phone:
                    primary.phone = alt.phone
                if not primary.company_name and alt.company_name:
                    primary.company_name = alt.company_name

            sources = sorted({s.source for s in group})
            q = await self.db.execute(
                select(UnifiedContact).where(
                    UnifiedContact.tenant_id == self.tenant_id,
                    UnifiedContact.normalized_key == key,
                )
            )
            row = q.scalar_one_or_none()
            if row is None:
                row = UnifiedContact(
                    tenant_id=self.tenant_id,
                    display_name=primary.display_name or "Sin nombre",
                    company_name=primary.company_name,
                    primary_email=(primary.email or "").lower() or None,
                    primary_phone=self._normalize_phone(primary.phone),
                    normalized_key=key,
                    sources=sources,
                    synced_at=now,
                )
                self.db.add(row)
                await self.db.flush()
                created += 1
            else:
                row.display_name = primary.display_name or row.display_name
                row.company_name = primary.company_name or row.company_name
                row.primary_email = (primary.email or row.primary_email or "").lower() or None
                row.primary_phone = self._normalize_phone(primary.phone) or row.primary_phone
                row.sources = sources
                row.synced_at = now
                updated += 1

            await self.db.execute(
                delete(UnifiedContactIdentity).where(UnifiedContactIdentity.contact_id == row.id)
            )
            for seed in group:
                self.db.add(
                    UnifiedContactIdentity(
                        tenant_id=self.tenant_id,
                        contact_id=row.id,
                        source=seed.source,
                        external_id=seed.external_id,
                        display_name=seed.display_name,
                        email=seed.email,
                        phone=seed.phone,
                        company_name=seed.company_name,
                        profile_url=seed.profile_url,
                        extra=seed.extra or {},
                    )
                )

        await self.db.commit()
        total_q = await self.db.execute(
            select(func.count()).select_from(UnifiedContact).where(UnifiedContact.tenant_id == self.tenant_id)
        )
        return UnifiedContactSyncResponse(
            created=created,
            updated=updated,
            total=int(total_q.scalar() or 0),
            sources_synced=sorted({s.source for s in seeds}),
        )

    async def list_contacts(self, *, search: str = "", limit: int = 50, sync: bool = True) -> UnifiedContactListResponse:
        if sync:
            count_q = await self.db.execute(
                select(func.count()).select_from(UnifiedContact).where(UnifiedContact.tenant_id == self.tenant_id)
            )
            if int(count_q.scalar() or 0) == 0:
                await self.sync_contacts()

        stmt = select(UnifiedContact).where(UnifiedContact.tenant_id == self.tenant_id)
        if search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    UnifiedContact.display_name.ilike(term),
                    UnifiedContact.company_name.ilike(term),
                    UnifiedContact.primary_email.ilike(term),
                    UnifiedContact.primary_phone.ilike(term),
                )
            )
        stmt = stmt.order_by(UnifiedContact.display_name.asc()).limit(limit)
        rows = (await self.db.execute(stmt)).scalars().all()
        return UnifiedContactListResponse(
            items=[self._to_response(r) for r in rows],
            total=len(rows),
        )

    async def get_profile(self, contact_id: uuid.UUID) -> UnifiedContactProfile360 | None:
        q = await self.db.execute(
            select(UnifiedContact).where(
                UnifiedContact.id == contact_id,
                UnifiedContact.tenant_id == self.tenant_id,
            )
        )
        row = q.scalar_one_or_none()
        if row is None:
            return None

        id_q = await self.db.execute(
            select(UnifiedContactIdentity).where(UnifiedContactIdentity.contact_id == contact_id)
        )
        identities = list(id_q.scalars().all())

        query_term = row.company_name or row.display_name
        search = CommunicationsSearchService(self.db, self.tenant_id, self.user_id)
        unified = await search.unified_search(query_term, limit_per_group=5)

        stats = await self._build_stats(row, identities)
        odoo_summary = await self._odoo_summary(identities)
        dgcp_items = await self._dgcp_items(row)

        emails = list(dict.fromkeys(filter(None, [row.primary_email] + [i.email for i in identities])))
        phones = list(dict.fromkeys(filter(None, [row.primary_phone] + [i.phone for i in identities])))

        return UnifiedContactProfile360(
            contact=self._to_response(row),
            identities=[UnifiedContactIdentityResponse.model_validate(i) for i in identities],
            emails=emails,
            phones=phones,
            stats=stats,
            timeline=unified.timeline[:15],
            search_groups=unified.groups[:8],
            odoo_summary=odoo_summary,
            dgcp_opportunities=dgcp_items,
        )

    async def _collect_seeds(self, limit: int) -> list[_IdentitySeed]:
        seeds: list[_IdentitySeed] = []

        session_q = await self.db.execute(
            select(WhatsappSession.id).where(
                WhatsappSession.tenant_id == self.tenant_id,
                WhatsappSession.user_id == self.user_id,
                WhatsappSession.is_active.is_(True),
            )
        )
        wa_sessions = [r[0] for r in session_q.all()]
        if wa_sessions:
            chats = (
                await self.db.execute(
                    select(WhatsappChat)
                    .where(WhatsappChat.tenant_id == self.tenant_id, WhatsappChat.session_id.in_(wa_sessions))
                    .limit(limit)
                )
            ).scalars().all()
            for chat in chats:
                phone = self._phone_from_jid(chat.remote_jid)
                seeds.append(
                    _IdentitySeed(
                        source="whatsapp",
                        external_id=str(chat.id),
                        display_name=chat.name or phone or chat.remote_jid,
                        phone=phone,
                        profile_url=f"/comunicaciones?tab=whatsapp&chat={chat.id}",
                        extra={"remote_jid": chat.remote_jid, "is_group": chat.is_group},
                    )
                )

        odoo = OdooService(self.db, self.tenant_id, user_id=self.user_id)
        customers = await odoo.list_customers(limit=limit)
        for c in customers.items:
            seeds.append(
                _IdentitySeed(
                    source="odoo",
                    external_id=str(c.id),
                    display_name=c.name or f"Partner {c.id}",
                    email=c.email,
                    phone=c.phone,
                    company_name=c.name if c.is_company else None,
                    profile_url=f"/odoo/customers/{c.id}",
                    extra={"vat": c.vat, "city": c.city, "is_company": c.is_company},
                )
            )

        conn = await M365ConnectionService(self.db, self.tenant_id, self.user_id).connection_state()
        if conn.account_connected:
            try:
                m365 = M365Service(self.db, self.tenant_id, user_id=self.user_id)
                outlook = await m365.contacts(limit=limit)
                for item in outlook.items:
                    if isinstance(item, dict):
                        seeds.append(
                            _IdentitySeed(
                                source="outlook",
                                external_id=str(item.get("id") or item.get("display_name")),
                                display_name=item.get("display_name") or "Contacto",
                                email=item.get("email"),
                                company_name=item.get("company"),
                                profile_url="/comunicaciones?tab=outlook",
                            )
                        )
                    else:
                        seeds.append(
                            _IdentitySeed(
                                source="outlook",
                                external_id=str(getattr(item, "id", None) or getattr(item, "display_name", "")),
                                display_name=getattr(item, "display_name", None) or "Contacto",
                                email=getattr(item, "email", None),
                                company_name=getattr(item, "company", None),
                                profile_url="/comunicaciones?tab=outlook",
                            )
                        )
                teams_resp = await m365.teams(limit=min(limit, 30))
                for team in teams_resp.items:
                    name = getattr(team, "display_name", None) or (team.get("display_name") if isinstance(team, dict) else None)
                    tid = getattr(team, "id", None) or (team.get("id") if isinstance(team, dict) else None)
                    desc = getattr(team, "description", None) or (team.get("description") if isinstance(team, dict) else None)
                    seeds.append(
                        _IdentitySeed(
                            source="teams",
                            external_id=str(tid or name),
                            display_name=name or "Equipo Teams",
                            company_name=desc,
                            profile_url="/comunicaciones?tab=teams",
                        )
                    )
            except GraphError:
                pass

        dgcp_q = await self.db.execute(
            select(DGCPOpportunity.institution)
            .where(DGCPOpportunity.tenant_id == self.tenant_id)
            .distinct()
            .limit(limit)
        )
        for (institution,) in dgcp_q.all():
            if not institution:
                continue
            norm = _normalize(institution)
            seeds.append(
                _IdentitySeed(
                    source="dgcp",
                    external_id=f"inst:{norm[:64]}",
                    display_name=institution,
                    company_name=institution,
                    profile_url="/dgcp",
                    extra={"type": "institution"},
                )
            )

        return seeds

    async def _build_stats(self, contact: UnifiedContact, identities: list[UnifiedContactIdentity]) -> UnifiedContactStats:
        name_term = f"%{contact.display_name}%"
        company_term = f"%{contact.company_name}%" if contact.company_name else name_term

        tasks_q = await self.db.execute(
            select(func.count())
            .select_from(Task)
            .where(
                Task.tenant_id == self.tenant_id,
                or_(Task.customer_name.ilike(name_term), Task.customer_name.ilike(company_term)),
            )
        )
        dgcp_q = await self.db.execute(
            select(func.count())
            .select_from(DGCPOpportunity)
            .where(
                DGCPOpportunity.tenant_id == self.tenant_id,
                DGCPOpportunity.institution.ilike(company_term if contact.company_name else name_term),
            )
        )
        wa_ids = [i.external_id for i in identities if i.source == "whatsapp"]
        wa_msgs = 0
        if wa_ids:
            from app.models.whatsapp import WhatsappMessage

            msg_q = await self.db.execute(
                select(func.count())
                .select_from(WhatsappMessage)
                .where(WhatsappMessage.chat_id.in_([uuid.UUID(x) for x in wa_ids if self._is_uuid(x)]))
            )
            wa_msgs = int(msg_q.scalar() or 0)

        return UnifiedContactStats(
            whatsapp_chats=len(wa_ids),
            whatsapp_messages=wa_msgs,
            tasks=int(tasks_q.scalar() or 0),
            dgcp_opportunities=int(dgcp_q.scalar() or 0),
            linked_sources=len({i.source for i in identities}),
        )

    async def _odoo_summary(self, identities: list[UnifiedContactIdentity]) -> dict | None:
        odoo_ids = [int(i.external_id) for i in identities if i.source == "odoo" and i.external_id.isdigit()]
        if not odoo_ids:
            return None
        try:
            odoo = OdooService(self.db, self.tenant_id, user_id=self.user_id)
            detail = await OdooDetailService(odoo).get_customer_detail(odoo_ids[0])
            return {
                "partner_id": detail.id,
                "name": detail.name,
                "email": detail.email,
                "phone": detail.phone,
                "open_opportunities": len(detail.opportunities or []),
                "open_quotations": len(detail.quotations or []),
                "open_invoices": len(detail.open_invoices or []),
            }
        except Exception:
            return {"partner_id": odoo_ids[0], "linked": True}

    async def _dgcp_items(self, contact: UnifiedContact) -> list[dict]:
        term = f"%{contact.company_name or contact.display_name}%"
        q = await self.db.execute(
            select(DGCPOpportunity)
            .where(DGCPOpportunity.tenant_id == self.tenant_id, DGCPOpportunity.institution.ilike(term))
            .order_by(DGCPOpportunity.deadline.desc())
            .limit(8)
        )
        return [
            {
                "id": str(o.id),
                "code": o.code,
                "title": o.title[:120],
                "institution": o.institution,
                "deadline": o.deadline.isoformat(),
                "status": o.status,
                "url": f"/dgcp/{o.id}",
            }
            for o in q.scalars().all()
        ]

    @staticmethod
    def _is_uuid(value: str) -> bool:
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False

    def _to_response(self, row: UnifiedContact) -> UnifiedContactResponse:
        return UnifiedContactResponse(
            id=row.id,
            display_name=row.display_name,
            company_name=row.company_name,
            primary_email=row.primary_email,
            primary_phone=row.primary_phone,
            sources=list(row.sources or []),
            source_labels=[self.SOURCE_LABELS.get(s, s) for s in (row.sources or [])],
            tags=list(row.tags or []),
            last_activity_at=row.last_activity_at,
            synced_at=row.synced_at,
        )
