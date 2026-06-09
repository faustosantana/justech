"""Búsqueda empresarial global — SQL + Odoo read-only (Fase 6 + orquestador 6.5)."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dgcp_opportunity import DGCPOpportunity
from app.schemas.search import EnterpriseSearchResponse, SearchResultGroup, SearchResultItem
from app.services.notification_service import NotificationService
from app.services.odoo_service import OdooService
from app.services.task_service import TaskService

GROUP_LABELS = {
    "customers": "Clientes",
    "products": "Productos",
    "invoices": "Facturas",
    "quotations": "Cotizaciones",
    "opportunities": "Oportunidades",
    "vendors": "Proveedores",
    "projects": "Proyectos",
    "tasks": "Tareas",
    "notifications": "Notificaciones",
    "dgcp": "Licitaciones DGCP",
    "documents": "Documentos",
    "knowledge": "Conocimiento corporativo",
    "documents_future": "Documentos (futuro)",
    "email_future": "Correo M365 (futuro)",
}

PER_GROUP_LIMIT = 8


class EnterpriseSearchService:
    """Motor de búsqueda estructurada — delega aceleración al orquestador 6.5."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.odoo = OdooService(db, tenant_id, user_id=user_id)
        self.tasks = TaskService(db, tenant_id, user_id=user_id)
        self.notifications = NotificationService(db, tenant_id)

    @staticmethod
    def _score(query: str, *texts: str | None) -> float:
        q = query.lower().strip()
        if not q:
            return 0.0
        best = 0.0
        for raw in texts:
            if not raw:
                continue
            t = raw.lower()
            if t == q:
                best = max(best, 100.0)
            elif t.startswith(q):
                best = max(best, 90.0)
            elif q in t:
                best = max(best, 75.0)
            else:
                tokens = [w for w in re.split(r"\s+", q) if len(w) >= 2]
                if tokens and all(tok in t for tok in tokens):
                    best = max(best, 60.0)
        return best or 40.0

    def _item(
        self,
        *,
        id_: str | int | uuid.UUID,
        type_: str,
        title: str,
        subtitle: str | None,
        description: str | None,
        source: str,
        url: str,
        company: str | None,
        query: str,
        metadata: dict | None = None,
    ) -> SearchResultItem:
        return SearchResultItem(
            id=str(id_),
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

    async def search(
        self,
        query: str,
        *,
        source_filter: str | None = None,
        type_filter: str | None = None,
        company_filter: str | None = None,
        limit_per_group: int = PER_GROUP_LIMIT,
        channel: str = "api",
    ) -> EnterpriseSearchResponse:
        from app.services.search_acceleration_orchestrator import SearchAccelerationOrchestrator

        orchestrator = SearchAccelerationOrchestrator(self.db, self.tenant_id, self.user_id)
        effective_company = company_filter
        if not effective_company and self.user_id:
            from app.services.global_company_context_service import GlobalCompanyContextService

            names = await GlobalCompanyContextService(
                self.db, self.tenant_id, self.user_id
            ).get_active_company_names()
            if names:
                effective_company = names[0] if len(names) == 1 else "|".join(names)
        return await orchestrator.search(
            query,
            source_filter=source_filter,
            type_filter=type_filter,
            company_filter=effective_company,
            limit_per_group=limit_per_group,
            channel=channel,
        )

    async def search_odoo(
        self,
        query: str,
        *,
        limit_per_group: int = PER_GROUP_LIMIT,
        company_filter: str | None = None,
    ) -> tuple[list[SearchResultGroup], list[str]]:
        q = query.strip()
        groups: list[SearchResultGroup] = []
        odoo_health = await self.odoo.health()
        if not odoo_health.connected:
            return [], []

        company_name = odoo_health.active_company_name
        sources = ["odoo"]

        async def _add(group_type: str, label: str, items: list[SearchResultItem]) -> None:
            if company_filter:
                items = [i for i in items if i.company and company_filter.lower() in i.company.lower()]
            if not items:
                return
            items.sort(key=lambda x: x.score, reverse=True)
            groups.append(
                SearchResultGroup(
                    type=group_type, label=label, count=min(len(items), limit_per_group),
                    items=items[:limit_per_group],
                )
            )

        customers = await self.odoo.list_customers(search=q, limit=limit_per_group)
        await _add(
            "customers",
            GROUP_LABELS["customers"],
            [
                self._item(
                    id_=c.id, type_="cliente", title=c.name, subtitle=c.email or c.vat,
                    description=c.city, source="odoo", url=f"/odoo/customers/{c.id}",
                    company=company_name, query=q, metadata={"vat": c.vat},
                )
                for c in customers.items
            ],
        )

        products = await self.odoo.list_products(search=q, limit=limit_per_group)
        await _add(
            "products",
            GROUP_LABELS["products"],
            [
                self._item(
                    id_=p.id, type_="producto", title=p.name, subtitle=p.default_code,
                    description=f"Precio: {p.list_price}" if p.list_price else None,
                    source="odoo", url=f"/odoo/products/{p.id}", company=company_name, query=q,
                )
                for p in products.items
            ],
        )

        vendors = await self.odoo.list_vendors(search=q, limit=limit_per_group)
        await _add(
            "vendors",
            GROUP_LABELS["vendors"],
            [
                self._item(
                    id_=v.id, type_="proveedor", title=v.name, subtitle=v.email,
                    description=v.city, source="odoo", url=f"/odoo/vendors/{v.id}",
                    company=company_name, query=q,
                )
                for v in vendors.items
            ],
        )

        invoices = await self.odoo.search_invoices(search=q, limit=limit_per_group)
        await _add(
            "invoices",
            GROUP_LABELS["invoices"],
            [
                self._item(
                    id_=inv.id, type_="factura", title=inv.name, subtitle=inv.partner_name,
                    description=f"Saldo: {inv.amount_residual} {inv.currency}",
                    source="odoo", url=f"/odoo/invoices/{inv.id}", company=company_name, query=q,
                    metadata={"payment_state": inv.payment_state},
                )
                for inv in invoices.items
            ],
        )

        quotations = await self.odoo.search_quotations(search=q, limit=limit_per_group)
        await _add(
            "quotations",
            GROUP_LABELS["quotations"],
            [
                self._item(
                    id_=qt.id, type_="cotización", title=qt.name, subtitle=qt.partner_name,
                    description=f"Total: {qt.amount_total}", source="odoo", url="/odoo",
                    company=company_name, query=q,
                )
                for qt in quotations.items
            ],
        )

        opportunities = await self.odoo.search_opportunities(search=q, limit=limit_per_group)
        await _add(
            "opportunities",
            GROUP_LABELS["opportunities"],
            [
                self._item(
                    id_=op.id, type_="oportunidad", title=op.name, subtitle=op.partner_name,
                    description=op.stage, source="odoo", url="/odoo", company=company_name, query=q,
                )
                for op in opportunities.items
            ],
        )

        projects = await self.odoo.search_projects(search=q, limit=limit_per_group)
        await _add(
            "projects",
            GROUP_LABELS["projects"],
            [
                self._item(
                    id_=pr.id, type_="proyecto", title=pr.name, subtitle=pr.partner_name,
                    description=pr.stage, source="odoo", url="/odoo", company=company_name, query=q,
                )
                for pr in projects.items
            ],
        )

        return groups, sources

    async def search_dgcp_direct(
        self,
        query: str,
        *,
        limit_per_group: int = PER_GROUP_LIMIT,
        company_filter: str | None = None,
    ) -> SearchResultGroup | None:
        q = query.strip()
        pattern = f"%{q}%"
        dgcp_result = await self.db.execute(
            select(DGCPOpportunity)
            .where(
                DGCPOpportunity.tenant_id == self.tenant_id,
                or_(
                    DGCPOpportunity.title.ilike(pattern),
                    DGCPOpportunity.institution.ilike(pattern),
                    DGCPOpportunity.code.ilike(pattern),
                    DGCPOpportunity.description.ilike(pattern),
                ),
            )
            .order_by(DGCPOpportunity.score.desc())
            .limit(limit_per_group)
        )
        items = [
            self._item(
                id_=row.id, type_="licitación", title=row.title[:200], subtitle=row.institution,
                description=f"Código {row.code} · vence {row.deadline}",
                source="dgcp", url=f"/dgcp/{row.id}", company=row.company, query=q,
                metadata={"code": row.code, "status": row.status},
            )
            for row in dgcp_result.scalars().all()
        ]
        if company_filter:
            items = [i for i in items if i.company and company_filter.lower() in i.company.lower()]
        if not items:
            return None
        items.sort(key=lambda x: x.score, reverse=True)
        return SearchResultGroup(
            type="dgcp", label=GROUP_LABELS["dgcp"], count=len(items), items=items
        )

    async def search_jaios_direct(
        self,
        query: str,
        *,
        limit_per_group: int = PER_GROUP_LIMIT,
        include_tasks: bool = True,
        include_notifications: bool = True,
    ) -> list[SearchResultGroup]:
        q = query.strip()
        groups: list[SearchResultGroup] = []

        if include_tasks:
            task_list = await self.tasks.list_tasks(search=q, limit=limit_per_group)
            task_items = [
                self._item(
                    id_=t.id, type_="tarea", title=t.title,
                    subtitle=t.assigned_to_name or t.suggested_assignee_name,
                    description=t.customer_name or t.description,
                    source="jaios", url=f"/tasks/{t.id}", company=t.department, query=q,
                    metadata={"status": t.status, "priority": t.priority},
                )
                for t in task_list.items
            ]
            if task_items:
                groups.append(
                    SearchResultGroup(
                        type="tasks", label=GROUP_LABELS["tasks"],
                        count=len(task_items), items=task_items,
                    )
                )

        if include_notifications:
            notif_result = await self.notifications.search_for_user(
                self.user_id, q, limit=limit_per_group
            )
            notif_items = [
                self._item(
                    id_=n.id, type_="notificación", title=n.title, subtitle=n.type,
                    description=n.message[:200] if n.message else None,
                    source="jaios",
                    url=f"/tasks/{n.related_task_id}" if n.related_task_id else "/notifications",
                    company=None, query=q,
                )
                for n in notif_result
            ]
            if notif_items:
                groups.append(
                    SearchResultGroup(
                        type="notifications", label=GROUP_LABELS["notifications"],
                        count=len(notif_items), items=notif_items,
                    )
                )

        return groups

    async def search_direct(
        self,
        query: str,
        *,
        source_filter: str | None = None,
        type_filter: str | None = None,
        company_filter: str | None = None,
        limit_per_group: int = PER_GROUP_LIMIT,
    ) -> EnterpriseSearchResponse:
        """Fallback Fase 6 — sin cache ni índice."""
        q = query.strip()
        if len(q) < 2:
            return EnterpriseSearchResponse(query=q, total=0, groups=[])

        groups: list[SearchResultGroup] = []
        sources_searched: list[str] = []

        if source_filter in (None, "odoo"):
            odoo_groups, odoo_src = await self.search_odoo(
                q, limit_per_group=limit_per_group, company_filter=company_filter
            )
            groups.extend(odoo_groups)
            sources_searched.extend(odoo_src)

        if source_filter in (None, "dgcp"):
            dgcp_g = await self.search_dgcp_direct(
                q, limit_per_group=limit_per_group, company_filter=company_filter
            )
            if dgcp_g:
                groups.append(dgcp_g)
                sources_searched.append("dgcp")

        if source_filter in (None, "jaios"):
            groups.extend(await self.search_jaios_direct(q, limit_per_group=limit_per_group))
            sources_searched.append("jaios")

        if type_filter:
            groups = [g for g in groups if g.type == type_filter]

        total = sum(g.count for g in groups)
        return EnterpriseSearchResponse(
            query=q,
            total=total,
            groups=groups,
            sources_searched=list(dict.fromkeys(sources_searched)),
            future_sources=["m365", "qdrant", "hermes"],
        )
