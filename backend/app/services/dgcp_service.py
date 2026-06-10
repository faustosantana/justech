import uuid
from datetime import date
from decimal import Decimal

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import not_found
from app.models.audit_log import AuditLog
from app.models.dgcp_history import DGCPOpportunityHistory
from app.models.dgcp_opportunity import DGCPOpportunity
from app.schemas.dgcp import (
    ACTION_TO_STATUS,
    DGCPOpportunityActionRequest,
    DGCPOpportunityListResponse,
    DGCPOpportunityResponse,
    DGCPOpportunitySummary,
    DGCPOpportunityUpdate,
    DGCPAuditLogResponse,
    DGCPOpportunityHistoryResponse,
    OpportunityCompany,
    OpportunityPriority,
    OpportunityStatus,
)
from app.services.audit_service import AuditService
from app.services.dgcp_classifier import classify_proceso_async
from app.services.dgcp_scorer import score_proceso
from integrations.dgcp.schemas import DGCPProcesoRecord


class DGCPService:
    CLOSED_STATUSES = frozenset({"won", "lost", "discarded"})

    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AuditService(db)

    @staticmethod
    def vigente_filters(*, include_expired: bool = False):
        """Procesos con plazo vigente (compras/contrataciones activas)."""
        if include_expired:
            return ()
        today = date.today()
        return (
            DGCPOpportunity.deadline >= today,
            DGCPOpportunity.status.notin_(tuple(DGCPService.CLOSED_STATUSES)),
        )

    async def list_opportunities(
        self,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
        status: OpportunityStatus | None = None,
        company: OpportunityCompany | None = None,
        priority: OpportunityPriority | None = None,
        skip: int = 0,
        limit: int = 100,
        include_expired: bool = False,
    ) -> DGCPOpportunityListResponse:
        base_filter = DGCPOpportunity.tenant_id == tenant_id
        for clause in self.vigente_filters(include_expired=include_expired):
            base_filter = base_filter & clause
        query = (
            select(DGCPOpportunity)
            .where(base_filter)
            .order_by(DGCPOpportunity.score.desc(), DGCPOpportunity.deadline.asc())
            .offset(skip)
            .limit(limit)
        )
        if user_id:
            from app.services.company_scope_filter import CompanyScopeFilter

            keys = await CompanyScopeFilter(self.db, tenant_id, user_id).dgcp_company_keys()
            if keys:
                query = query.where(DGCPOpportunity.company.in_(keys))
                base_filter = base_filter & DGCPOpportunity.company.in_(keys)
        if status:
            query = query.where(DGCPOpportunity.status == status.value)
        if company:
            query = query.where(DGCPOpportunity.company == company.value)
        if priority:
            query = query.where(DGCPOpportunity.priority == priority.value)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        count_query = select(func.count()).select_from(DGCPOpportunity).where(base_filter)
        if status:
            count_query = count_query.where(DGCPOpportunity.status == status.value)
        if company:
            count_query = count_query.where(DGCPOpportunity.company == company.value)
        if priority:
            count_query = count_query.where(DGCPOpportunity.priority == priority.value)
        total = (await self.db.execute(count_query)).scalar_one()

        summary = await self.compute_dashboard(
            tenant_id,
            user_id=user_id,
            include_expired=include_expired,
        )
        return DGCPOpportunityListResponse(
            items=[DGCPOpportunityResponse.model_validate(i) for i in items],
            summary=summary,
            total=total,
        )

    async def get_opportunity(self, tenant_id: uuid.UUID, opportunity_id: uuid.UUID) -> DGCPOpportunity:
        result = await self.db.execute(
            select(DGCPOpportunity).where(
                DGCPOpportunity.id == opportunity_id,
                DGCPOpportunity.tenant_id == tenant_id,
            )
        )
        opportunity = result.scalar_one_or_none()
        if not opportunity:
            raise not_found("Opportunity not found")
        return opportunity

    async def update_opportunity(
        self,
        tenant_id: uuid.UUID,
        opportunity_id: uuid.UUID,
        data: DGCPOpportunityUpdate,
        *,
        user_id: uuid.UUID | None = None,
        request: Request | None = None,
    ) -> DGCPOpportunity:
        opportunity = await self.get_opportunity(tenant_id, opportunity_id)
        from_status = opportunity.status
        if data.status:
            opportunity.status = data.status.value
            await self._record_history(
                tenant_id=tenant_id,
                opportunity_id=opportunity.id,
                user_id=user_id,
                action="status_change",
                from_status=from_status,
                to_status=opportunity.status,
                notes=data.notes,
            )
            await self.audit.log(
                action="dgcp.opportunity.status_change",
                tenant_id=tenant_id,
                user_id=user_id,
                resource_type="dgcp_opportunity",
                resource_id=opportunity.id,
                details={
                    "code": opportunity.code,
                    "from_status": from_status,
                    "to_status": opportunity.status,
                    "notes": data.notes,
                },
                request=request,
            )
        await self.db.flush()
        await self.db.refresh(opportunity)
        return opportunity

    async def apply_action(
        self,
        tenant_id: uuid.UUID,
        opportunity_id: uuid.UUID,
        data: DGCPOpportunityActionRequest,
        *,
        user_id: uuid.UUID | None = None,
        request: Request | None = None,
    ) -> DGCPOpportunity:
        opportunity = await self.get_opportunity(tenant_id, opportunity_id)
        from_status = opportunity.status
        to_status = ACTION_TO_STATUS[data.action].value
        opportunity.status = to_status

        await self._record_history(
            tenant_id=tenant_id,
            opportunity_id=opportunity.id,
            user_id=user_id,
            action=data.action.value,
            from_status=from_status,
            to_status=to_status,
            notes=data.notes,
        )
        await self.audit.log(
            action=f"dgcp.opportunity.{data.action.value}",
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type="dgcp_opportunity",
            resource_id=opportunity.id,
            details={
                "code": opportunity.code,
                "from_status": from_status,
                "to_status": to_status,
                "notes": data.notes,
            },
            request=request,
        )
        await self.db.flush()
        await self.db.refresh(opportunity)
        return opportunity

    async def get_history(
        self, tenant_id: uuid.UUID, opportunity_id: uuid.UUID
    ) -> list[DGCPOpportunityHistoryResponse]:
        await self.get_opportunity(tenant_id, opportunity_id)
        result = await self.db.execute(
            select(DGCPOpportunityHistory)
            .where(
                DGCPOpportunityHistory.tenant_id == tenant_id,
                DGCPOpportunityHistory.opportunity_id == opportunity_id,
            )
            .order_by(DGCPOpportunityHistory.created_at.desc())
        )
        return [DGCPOpportunityHistoryResponse.from_orm_history(row) for row in result.scalars().all()]

    async def list_audit_logs(
        self, tenant_id: uuid.UUID, *, limit: int = 50
    ) -> list[DGCPAuditLogResponse]:
        result = await self.db.execute(
            select(AuditLog)
            .where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.action.like("dgcp.%"),
            )
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return [DGCPAuditLogResponse.model_validate(row) for row in result.scalars().all()]

    async def compute_dashboard(
        self,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
        include_expired: bool = False,
    ) -> DGCPOpportunitySummary:
        base = DGCPOpportunity.tenant_id == tenant_id
        for clause in self.vigente_filters(include_expired=include_expired):
            base = base & clause
        if user_id:
            from app.services.company_scope_filter import CompanyScopeFilter

            keys = await CompanyScopeFilter(self.db, tenant_id, user_id).dgcp_company_keys()
            if keys:
                base = base & DGCPOpportunity.company.in_(keys)

        status_rows = await self.db.execute(
            select(DGCPOpportunity.status, func.count())
            .where(base)
            .group_by(DGCPOpportunity.status)
        )
        by_status = {row[0]: row[1] for row in status_rows.all()}

        company_rows = await self.db.execute(
            select(DGCPOpportunity.company, func.count())
            .where(base)
            .group_by(DGCPOpportunity.company)
        )
        by_company = {row[0]: row[1] for row in company_rows.all()}

        priority_rows = await self.db.execute(
            select(DGCPOpportunity.priority, func.count())
            .where(base)
            .group_by(DGCPOpportunity.priority)
        )
        by_priority = {row[0]: row[1] for row in priority_rows.all()}

        amount_company_rows = await self.db.execute(
            select(DGCPOpportunity.company, func.coalesce(func.sum(DGCPOpportunity.amount), 0))
            .where(base, DGCPOpportunity.status.notin_(["discarded", "lost"]))
            .group_by(DGCPOpportunity.company)
        )
        amount_by_company = {
            row[0]: Decimal(str(row[1])) for row in amount_company_rows.all()
        }

        total_amount_row = await self.db.execute(
            select(func.coalesce(func.sum(DGCPOpportunity.amount), 0)).where(
                base, DGCPOpportunity.status.notin_(["discarded", "lost"])
            )
        )
        total_amount = Decimal(str(total_amount_row.scalar_one()))

        from app.models.dgcp_bid_package import DGCPBidPackage

        pkg_query = (
            select(DGCPBidPackage.real_expediente_status, func.count())
            .join(DGCPOpportunity, DGCPOpportunity.id == DGCPBidPackage.opportunity_id)
            .where(DGCPOpportunity.tenant_id == tenant_id)
        )
        for clause in self.vigente_filters(include_expired=include_expired):
            pkg_query = pkg_query.where(clause)
        if user_id:
            from app.services.company_scope_filter import CompanyScopeFilter

            keys = await CompanyScopeFilter(self.db, tenant_id, user_id).dgcp_company_keys()
            if keys:
                pkg_query = pkg_query.where(DGCPOpportunity.company.in_(keys))

        presentation_rows = await self.db.execute(pkg_query.group_by(DGCPBidPackage.real_expediente_status))
        raw_presentation = {row[0] or "sin_generar": row[1] for row in presentation_rows.all()}
        presentation = {
            "sin_generar": raw_presentation.get("sin_generar", 0),
            "expediente_generado": sum(
                raw_presentation.get(k, 0)
                for k in (
                    "generado_incompleto",
                    "generado_con_observaciones",
                    "listo_para_revision",
                )
            ),
            "paquete_preparado": raw_presentation.get("paquete_dgcp_preparado", 0)
            + raw_presentation.get("descargado", 0),
            "listo_para_subir": raw_presentation.get("listo_para_subir", 0),
            "requiere_actualizacion": raw_presentation.get("requiere_actualizacion", 0),
        }

        return DGCPOpportunitySummary(
            total_opportunities=sum(by_status.values()),
            total_potential_amount=total_amount,
            by_status=by_status,
            by_company=by_company,
            by_priority=by_priority,
            amount_by_company=amount_by_company,
            to_bid=by_status.get(OpportunityStatus.TO_BID.value, 0),
            to_review=by_status.get(OpportunityStatus.TO_REVIEW.value, 0),
            discarded=by_status.get(OpportunityStatus.DISCARDED.value, 0),
            won=by_status.get(OpportunityStatus.WON.value, 0),
            lost=by_status.get(OpportunityStatus.LOST.value, 0),
            presentation=presentation,
        )

    async def reclassify_opportunities(
        self,
        tenant_id: uuid.UUID,
        *,
        use_ai: bool = True,
    ) -> dict[str, int | dict[str, int]]:
        result = await self.db.execute(
            select(DGCPOpportunity).where(DGCPOpportunity.tenant_id == tenant_id)
        )
        opportunities = list(result.scalars().all())
        by_company: dict[str, int] = {}
        updated = 0

        for opp in opportunities:
            payload = dict(opp.raw_payload or {})
            payload.setdefault("codigo_proceso", opp.code)
            payload.setdefault("unidad_compra", opp.institution)
            payload.setdefault("titulo", opp.title)
            payload.setdefault("descripcion", opp.description)
            payload.setdefault("objeto_proceso", opp.objeto_proceso)
            payload.setdefault("monto_estimado", float(opp.amount))
            payload.setdefault("divisa", opp.currency)
            record = DGCPProcesoRecord.from_api(payload)
            classification = await classify_proceso_async(
                record, self.db, tenant_id, use_ai=use_ai
            )
            scoring = score_proceso(record, classification)
            opp.company = classification.company
            opp.confidence_score = classification.confidence_score
            opp.classification_reason = classification.classification_reason
            opp.score = scoring.score
            opp.probability = scoring.probability
            opp.priority = scoring.priority
            opp.risks = scoring.risks
            opp.ai_recommendations = scoring.recommendations
            opp.suggested_action = scoring.suggested_action
            opp.justech_potential_amount = scoring.potential_amount
            by_company[classification.company] = by_company.get(classification.company, 0) + 1
            updated += 1

        await self.db.flush()
        unclassified = by_company.get("unclassified", 0)
        return {
            "total": updated,
            "reclassified": updated - unclassified,
            "unclassified": unclassified,
            "by_company": by_company,
        }

    async def _record_history(
        self,
        *,
        tenant_id: uuid.UUID,
        opportunity_id: uuid.UUID,
        user_id: uuid.UUID | None,
        action: str,
        from_status: str | None,
        to_status: str | None,
        notes: str | None,
    ) -> None:
        self.db.add(
            DGCPOpportunityHistory(
                tenant_id=tenant_id,
                opportunity_id=opportunity_id,
                user_id=user_id,
                action=action,
                from_status=from_status,
                to_status=to_status,
                notes=notes,
            )
        )
