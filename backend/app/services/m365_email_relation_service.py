"""Relación automática correos M365 → DGCP, Odoo, tareas."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.task import Task
from app.schemas.m365_operative import M365EmailRelation
from app.services.m365_email_classifier import M365EmailClassifier


class M365EmailRelationService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self._classifier = M365EmailClassifier()

    async def relate(
        self,
        *,
        subject: str,
        body: str,
        extracted: dict,
        classification: str,
    ) -> list[M365EmailRelation]:
        combined = f"{subject}\n{body}"
        relations: list[M365EmailRelation] = []
        code = extracted.get("dgcp_process_code") or self._classifier.dgcp_code(combined)
        if code:
            opp = await self._find_dgcp_by_code(code)
            if opp:
                relations.append(
                    M365EmailRelation(
                        entity_type="dgcp_opportunity",
                        entity_id=str(opp.id),
                        label=f"{opp.code} — {opp.title[:80]}",
                        confidence=92 if code.upper() in opp.code.upper() else 78,
                        href=f"/dgcp/{opp.id}",
                        metadata={"code": opp.code, "institution": opp.institution},
                    )
                )
        if not any(r.entity_type == "dgcp_opportunity" for r in relations):
            relations.extend(await self._fuzzy_dgcp(extracted, classification))
        client = extracted.get("client")
        if client:
            relations.append(
                M365EmailRelation(
                    entity_type="customer",
                    label=client,
                    confidence=85,
                    href="/odoo",
                    metadata={"customer_name": client},
                )
            )
        vendor = extracted.get("vendor")
        if vendor:
            relations.append(
                M365EmailRelation(
                    entity_type="vendor",
                    label=vendor,
                    confidence=80,
                    href="/prices",
                    metadata={"vendor": vendor},
                )
            )
        task_rel = await self._related_open_task(extracted, classification)
        if task_rel:
            relations.append(task_rel)
        return relations

    async def _find_dgcp_by_code(self, code: str) -> DGCPOpportunity | None:
        normalized = code.replace(" ", "-").upper()
        result = await self.db.execute(
            select(DGCPOpportunity).where(
                DGCPOpportunity.tenant_id == self.tenant_id,
                or_(
                    DGCPOpportunity.code.ilike(f"%{normalized}%"),
                    DGCPOpportunity.code.ilike(f"%{code}%"),
                ),
            ).limit(1)
        )
        return result.scalar_one_or_none()

    async def _fuzzy_dgcp(self, extracted: dict, classification: str) -> list[M365EmailRelation]:
        if classification not in ("cotizacion_proveedor", "licitacion", "ficha_tecnica", "catalogo"):
            return []
        terms: list[str] = []
        if extracted.get("client"):
            terms.append(str(extracted["client"]))
        for product in extracted.get("products") or []:
            terms.append(str(product))
        if not terms:
            return []
        query = select(DGCPOpportunity).where(DGCPOpportunity.tenant_id == self.tenant_id)
        for term in terms[:2]:
            query = query.where(
                or_(
                    DGCPOpportunity.title.ilike(f"%{term}%"),
                    DGCPOpportunity.institution.ilike(f"%{term}%"),
                )
            )
        result = await self.db.execute(query.limit(3))
        rows = list(result.scalars().all())
        return [
            M365EmailRelation(
                entity_type="dgcp_opportunity",
                entity_id=str(row.id),
                label=f"{row.code} — {row.institution[:60]}",
                confidence=68,
                href=f"/dgcp/{row.id}",
                metadata={"code": row.code},
            )
            for row in rows
        ]

    async def _related_open_task(self, extracted: dict, classification: str) -> M365EmailRelation | None:
        client = extracted.get("client")
        if not client:
            return None
        result = await self.db.execute(
            select(Task).where(
                Task.tenant_id == self.tenant_id,
                Task.status.in_(("pending", "in_progress")),
                Task.customer_name.ilike(f"%{client.split()[-1]}%"),
            ).limit(1)
        )
        task = result.scalar_one_or_none()
        if not task:
            return None
        return M365EmailRelation(
            entity_type="task",
            entity_id=str(task.id),
            label=task.title[:100],
            confidence=60,
            href=f"/tasks/{task.id}",
        )
