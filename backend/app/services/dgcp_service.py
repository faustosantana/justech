import uuid
from datetime import date
from decimal import Decimal

from fastapi import Request
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import not_found
from app.models.audit_log import AuditLog
from app.models.dgcp_history import DGCPOpportunityHistory
from app.models.dgcp_opportunity import DGCPOpportunity
from app.schemas.dgcp import (
    DGCPOpportunityActionRequest,
    DGCPOpportunityCreate,
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
from app.services.dgcp_funnel import (
    FunnelStage,
    build_funnel_guidance,
    normalize_action,
    statuses_for_funnel_stage,
    validate_transition,
)
from app.services.dgcp_scorer import score_proceso
from integrations.dgcp.schemas import DGCPProcesoRecord


class DGCPService:
    CLOSED_STATUSES = frozenset({
        "awarded", "won", "lost", "discarded", "cancelled",
    })
    COMMON_DGCP_CODE_TOKENS = frozenset({
        "DAF", "CD", "CM", "CCC", "PEEX", "CP", "2024", "2025", "2026", "2027", "2028",
    })

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

    @staticmethod
    def build_search_filter(search: str | None):
        """Búsqueda por código, título, institución, UUID parcial y tokens de código."""
        q = (search or "").strip()
        if len(q) < 2:
            return None
        try:
            opp_uuid = uuid.UUID(q)
            return DGCPOpportunity.id == opp_uuid
        except ValueError:
            pass

        normalized = q.upper().replace(" ", "").replace("/", "-")
        tokens = [t for t in normalized.split("-") if len(t) >= 2]
        pattern = f"%{q}%"

        # Búsqueda por palabras (institución, título): todas las palabras deben aparecer.
        if " " in q.strip() and "-" not in q.strip():
            words = [w.strip() for w in q.split() if len(w.strip()) >= 3]
            if words:
                word_filters = []
                for word in words:
                    wp = f"%{word}%"
                    word_filters.append(
                        or_(
                            DGCPOpportunity.title.ilike(wp),
                            DGCPOpportunity.institution.ilike(wp),
                            DGCPOpportunity.description.ilike(wp),
                            DGCPOpportunity.code.ilike(wp),
                        )
                    )
                return and_(*word_filters)

        # Códigos DGCP (ej. RESIDE-DAF-CD-2026): tokens distintivos en el código.
        if len(tokens) >= 2 and any(c.isalpha() for c in normalized):
            distinctive = [t for t in tokens if t not in DGCPService.COMMON_DGCP_CODE_TOKENS]
            if distinctive:
                code_and = and_(*[DGCPOpportunity.code.ilike(f"%{t}%") for t in tokens])
                return or_(
                    code_and,
                    DGCPOpportunity.code.ilike(f"%{normalized}%"),
                    DGCPOpportunity.title.ilike(pattern),
                    DGCPOpportunity.institution.ilike(pattern),
                    cast(DGCPOpportunity.id, String).ilike(pattern),
                )
            return or_(
                DGCPOpportunity.title.ilike(pattern),
                DGCPOpportunity.institution.ilike(pattern),
                DGCPOpportunity.description.ilike(pattern),
            )

        return or_(
            DGCPOpportunity.code.ilike(pattern),
            DGCPOpportunity.title.ilike(pattern),
            DGCPOpportunity.institution.ilike(pattern),
            DGCPOpportunity.description.ilike(pattern),
            cast(DGCPOpportunity.id, String).ilike(pattern),
        )

    @staticmethod
    def _responsible_name(opportunity: DGCPOpportunity) -> str | None:
        full_info = opportunity.full_info or {}
        name = full_info.get("responsible_name") or full_info.get("assignee")
        return str(name) if name else None

    @classmethod
    def to_response(cls, opportunity: DGCPOpportunity) -> DGCPOpportunityResponse:
        guidance = build_funnel_guidance(
            opportunity.status,
            needs_review=getattr(opportunity, "needs_review", False),
        )
        base = DGCPOpportunityResponse.model_validate(opportunity)
        return base.model_copy(
            update={
                "funnel_stage": guidance.funnel_stage,
                "funnel_stage_label": guidance.funnel_stage_label,
                "status_label": guidance.status_label,
                "next_recommended_action": guidance.next_recommended_action,
                "primary_action": guidance.primary_action,
                "available_actions": guidance.available_actions,
                "responsible_name": cls._responsible_name(opportunity),
            },
        )

    async def list_opportunities(
        self,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
        status: OpportunityStatus | None = None,
        funnel_stage: FunnelStage | None = None,
        company: OpportunityCompany | None = None,
        priority: OpportunityPriority | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
        include_expired: bool = False,
    ) -> DGCPOpportunityListResponse:
        search_clause = self.build_search_filter(search)
        if search_clause is not None:
            include_expired = True
        if funnel_stage in (
            FunnelStage.ADJUDICADAS,
            FunnelStage.NO_ADJUDICADAS,
            FunnelStage.DESCARTADAS,
        ):
            include_expired = True
        base_filter = DGCPOpportunity.tenant_id == tenant_id
        for clause in self.vigente_filters(include_expired=include_expired):
            base_filter = base_filter & clause
        if search_clause is not None:
            base_filter = base_filter & search_clause
        query = (
            select(DGCPOpportunity)
            .where(base_filter)
            .order_by(DGCPOpportunity.score.desc(), DGCPOpportunity.deadline.asc())
            .offset(skip)
            .limit(limit)
        )
        if user_id:
            from app.services.company_scope_filter import CompanyScopeFilter

            scope = CompanyScopeFilter(self.db, tenant_id, user_id)
            selected_keys = await scope.dgcp_company_keys()
            allowed_keys = await scope.allowed_dgcp_company_keys()
            if company:
                # Filtro explícito Empresa/RPE: no cruzar con el header (Just Office vs Justech).
                if allowed_keys and company.value not in allowed_keys and company.value != "unclassified":
                    query = query.where(DGCPOpportunity.id.is_(None))  # sin permiso → vacío
                    base_filter = base_filter & DGCPOpportunity.id.is_(None)
                else:
                    query = query.where(DGCPOpportunity.company == company.value)
                    base_filter = base_filter & (DGCPOpportunity.company == company.value)
            elif selected_keys:
                query = query.where(DGCPOpportunity.company.in_(selected_keys))
                base_filter = base_filter & DGCPOpportunity.company.in_(selected_keys)
        elif company:
            query = query.where(DGCPOpportunity.company == company.value)
            base_filter = base_filter & (DGCPOpportunity.company == company.value)
        if status:
            query = query.where(DGCPOpportunity.status == status.value)
        if funnel_stage:
            stage_statuses = statuses_for_funnel_stage(funnel_stage)
            query = query.where(DGCPOpportunity.status.in_(tuple(stage_statuses)))
        if priority:
            query = query.where(DGCPOpportunity.priority == priority.value)

        result = await self.db.execute(query)
        items = list(result.scalars().all())

        count_query = select(func.count()).select_from(DGCPOpportunity).where(base_filter)
        if status:
            count_query = count_query.where(DGCPOpportunity.status == status.value)
        if funnel_stage:
            stage_statuses = statuses_for_funnel_stage(funnel_stage)
            count_query = count_query.where(DGCPOpportunity.status.in_(tuple(stage_statuses)))
        if priority:
            count_query = count_query.where(DGCPOpportunity.priority == priority.value)
        total = (await self.db.execute(count_query)).scalar_one()

        summary = await self.compute_dashboard(
            tenant_id,
            user_id=user_id,
            include_expired=include_expired,
            company=company,
        )
        # Listado liviano: la inteligencia completa se carga en el detalle.
        slim_items = [
            self.to_response(i).model_copy(update={"jaios_intelligence": {}})
            for i in items
        ]
        return DGCPOpportunityListResponse(
            items=slim_items,
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
        action = normalize_action(data.action.value)
        to_status = validate_transition(from_status, action.value)
        opportunity.status = to_status

        if action.value == "desmarcar_interes":
            opportunity.needs_review = False
        elif action.value == "descartar":
            opportunity.needs_review = False

        # Responsable JAIOS (sin tocar Odoo): quien inicia interés/preparación
        if user_id and action.value in ("marcar_interes", "iniciar_preparacion"):
            info = dict(opportunity.full_info or {})
            info.setdefault("responsible_user_id", str(user_id))
            if action.value == "marcar_interes":
                info["interest_user_id"] = str(user_id)
            if action.value == "iniciar_preparacion":
                info["preparation_started_by"] = str(user_id)
            opportunity.full_info = info

        # Puente Odoo CRM (soft-fail): lead al iniciar preparación; won/lost al cerrar.
        odoo_sync: dict | None = None
        if user_id:
            try:
                from app.services.dgcp_odoo_crm_bridge import DGCPOdooCrmBridge

                bridge = DGCPOdooCrmBridge(self.db, tenant_id, user_id)
                if action.value == "iniciar_preparacion":
                    odoo_sync = await bridge.ensure_opportunity_on_prepare(opportunity)
                elif action.value == "marcar_adjudicada":
                    odoo_sync = await bridge.sync_outcome(opportunity, won=True)
                elif action.value == "marcar_no_adjudicada":
                    odoo_sync = await bridge.sync_outcome(opportunity, won=False)
            except Exception as exc:  # noqa: BLE001 — no bloquear embudo DGCP
                odoo_sync = {"ok": False, "error": str(exc)}

        await self._record_history(
            tenant_id=tenant_id,
            opportunity_id=opportunity.id,
            user_id=user_id,
            action=action.value,
            from_status=from_status,
            to_status=to_status,
            notes=data.notes,
        )
        await self.audit.log(
            action=f"dgcp.opportunity.{action.value}",
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type="dgcp_opportunity",
            resource_id=opportunity.id,
            details={
                "code": opportunity.code,
                "from_status": from_status,
                "to_status": to_status,
                "notes": data.notes,
                "odoo_sync": odoo_sync,
            },
            request=request,
        )
        await self.db.flush()
        await self.db.refresh(opportunity)
        return opportunity

    async def create_opportunity(
        self,
        tenant_id: uuid.UUID,
        data: DGCPOpportunityCreate,
        *,
        user_id: uuid.UUID | None = None,
        request: Request | None = None,
    ) -> DGCPOpportunity:
        existing = await self.db.execute(
            select(DGCPOpportunity).where(
                DGCPOpportunity.tenant_id == tenant_id,
                DGCPOpportunity.code == data.code,
            )
        )
        if existing.scalar_one_or_none():
            from fastapi import HTTPException
            raise HTTPException(status_code=409, detail=f"Ya existe una oportunidad con código {data.code}")

        full_info = dict(data.full_info or {})
        full_info["source"] = data.source
        if data.responsible_user_id:
            full_info["responsible_user_id"] = str(data.responsible_user_id)

        opportunity = DGCPOpportunity(
            tenant_id=tenant_id,
            code=data.code,
            institution=data.institution,
            title=data.title,
            amount=data.amount,
            currency=data.currency,
            probability=data.probability,
            score=data.score,
            status=data.status.value,
            priority=data.priority.value,
            company=data.company.value,
            deadline=data.deadline,
            description=data.description,
            modalidad=data.modalidad,
            source_url=data.source_url,
            full_info=full_info,
            similar_history=data.similar_history,
            risks=data.risks,
            ai_recommendations=data.ai_recommendations,
            suggested_action=data.suggested_action,
            justech_potential_amount=data.justech_potential_amount,
            raw_payload={"created_manually": True, "source": data.source},
        )
        self.db.add(opportunity)
        await self.db.flush()

        await self._record_history(
            tenant_id=tenant_id,
            opportunity_id=opportunity.id,
            user_id=user_id,
            action="create_manual",
            from_status=None,
            to_status=opportunity.status,
            notes=f"Creada manualmente ({data.source})",
        )
        await self.audit.log(
            action="dgcp.opportunity.create_manual",
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type="dgcp_opportunity",
            resource_id=opportunity.id,
            details={"code": opportunity.code, "source": data.source, "institution": data.institution},
            request=request,
        )
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
        company: OpportunityCompany | None = None,
    ) -> DGCPOpportunitySummary:
        base = DGCPOpportunity.tenant_id == tenant_id
        for clause in self.vigente_filters(include_expired=include_expired):
            base = base & clause
        if user_id:
            from app.services.company_scope_filter import CompanyScopeFilter

            scope = CompanyScopeFilter(self.db, tenant_id, user_id)
            selected_keys = await scope.dgcp_company_keys()
            allowed_keys = await scope.allowed_dgcp_company_keys()
            if company:
                if allowed_keys and company.value not in allowed_keys and company.value != "unclassified":
                    base = base & DGCPOpportunity.id.is_(None)
                else:
                    base = base & (DGCPOpportunity.company == company.value)
            elif selected_keys:
                base = base & DGCPOpportunity.company.in_(selected_keys)
        elif company:
            base = base & (DGCPOpportunity.company == company.value)

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
        # Reusar el mismo alcance de empresa que `base`
        if company:
            pkg_query = pkg_query.where(DGCPOpportunity.company == company.value)
        elif user_id:
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

        closed_base = DGCPOpportunity.tenant_id == tenant_id
        if company:
            closed_base = closed_base & (DGCPOpportunity.company == company.value)
        elif user_id:
            from app.services.company_scope_filter import CompanyScopeFilter

            keys = await CompanyScopeFilter(self.db, tenant_id, user_id).dgcp_company_keys()
            if keys:
                closed_base = closed_base & DGCPOpportunity.company.in_(keys)
        closed_rows = await self.db.execute(
            select(DGCPOpportunity.status, func.count())
            .where(
                closed_base,
                DGCPOpportunity.status.in_(("won", "awarded", "lost", "discarded", "cancelled")),
            )
            .group_by(DGCPOpportunity.status)
        )
        closed_by_status = {row[0]: row[1] for row in closed_rows.all()}

        return DGCPOpportunitySummary(
            total_opportunities=sum(by_status.values()),
            total_potential_amount=total_amount,
            by_status=by_status,
            by_company=by_company,
            by_priority=by_priority,
            amount_by_company=amount_by_company,
            to_bid=by_status.get(OpportunityStatus.TO_BID.value, 0),
            to_review=by_status.get(OpportunityStatus.TO_REVIEW.value, 0),
            discarded=by_status.get(OpportunityStatus.DISCARDED.value, 0)
            + closed_by_status.get(OpportunityStatus.DISCARDED.value, 0)
            + closed_by_status.get("cancelled", 0),
            won=by_status.get(OpportunityStatus.WON.value, 0)
            + by_status.get(OpportunityStatus.AWARDED.value, 0)
            + closed_by_status.get(OpportunityStatus.WON.value, 0)
            + closed_by_status.get("awarded", 0),
            lost=by_status.get(OpportunityStatus.LOST.value, 0)
            + closed_by_status.get(OpportunityStatus.LOST.value, 0),
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
