"""Oferta económica DGCP — adjuntar cotización Odoo, borradores y tareas."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models.dgcp_opportunity import DGCPOpportunity
from app.models.dgcp_process_document import DGCPProcessDocument
from app.models.economic_offer_draft import EconomicOfferDraft
from app.models.task import Task
from app.schemas.dgcp_economic_offer import (
    AttachOdooQuotationRequest,
    AttachOdooQuotationResponse,
    CreateEconomicOfferDraftTaskRequest,
    CreateEconomicOfferTaskResponse,
    EconomicOfferStatusResponse,
    EconomicOfferSuggestedProduct,
)
from app.schemas.tasks import TaskCreateRequest
from app.services.audit_service import AuditService
from app.services.dgcp_bid_package_service import ACTIVE_TASK_STATUSES, DGCPBidPackageService
from app.services.dgcp_compliance_engine import COMPLIANT_STATUSES, DGCPComplianceEngine
from app.services.dgcp_process_storage_service import DGCPProcessStorageService
from app.services.odoo_quotation_service import OdooQuotationService
from app.services.odoo_service import OdooService
from app.services.price_intelligence_service import PriceIntelligenceService
from app.services.task_service import TaskService


ECONOMIC_OFFER_KEY = "oferta_economica"
COMPLIANT_ECONOMIC_STATUSES = frozenset({"adjuntado", "validado_manual"})


class DGCPEconomicOfferService:
    def __init__(self, db, tenant_id: uuid.UUID, *, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.audit = AuditService(db)
        self.bid_svc = DGCPBidPackageService(db, tenant_id, user_id=user_id)
        self.compliance = DGCPComplianceEngine()
        self.odoo = OdooService(db, tenant_id, user_id=user_id)
        self.quotations = OdooQuotationService(self.odoo)

    async def search_audit(self, *, query: str, result_count: int) -> None:
        if not self.user_id:
            return
        await self.audit.log(
            action="dgcp.economic_offer.search",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="odoo_quotation",
            details={"query": query, "result_count": result_count},
        )
        await self.db.commit()

    async def get_status(self, opportunity_id: uuid.UUID) -> EconomicOfferStatusResponse:
        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")

        item = await self._find_economic_offer_item(opportunity_id)
        pkg = await self.bid_svc._get_package(opportunity_id)
        bid = pkg.bid_package if pkg else {}
        prep = float(bid.get("preparation_pct") or 0)

        draft = await self._get_draft(opportunity_id, item)
        suggested = await self._suggest_products(opportunity)

        status = item.get("status", "faltante") if item else "faltante"
        meta = item.get("economic_offer_meta") or {} if item else {}
        is_compliant = status in COMPLIANT_ECONOMIC_STATUSES and self._has_evidence(item or {})

        return EconomicOfferStatusResponse(
            opportunity_id=opportunity_id,
            opportunity_code=opportunity.code,
            requirement_id=uuid.UUID(str(item["id"])) if item and item.get("id") else None,
            checklist_status=status,
            display_status=self.compliance.display_status_label(status),
            is_compliant=is_compliant,
            has_odoo_quotation=bool(item and item.get("odoo_quotation_id")),
            odoo_quotation_id=item.get("odoo_quotation_id") if item else None,
            odoo_quotation_name=item.get("odoo_quotation_name") if item else None,
            process_document_id=uuid.UUID(str(item["process_document_id"]))
            if item and item.get("process_document_id")
            else None,
            document_title=item.get("document_title") if item else None,
            preparation_pct=prep,
            draft_status=draft.status if draft else None,
            draft_id=draft.id if draft else None,
            task_id=uuid.UUID(str(item["task_id"])) if item and item.get("task_id") else (draft.task_id if draft else None),
            suggested_products=suggested,
            metadata=meta,
        )

    async def attach_odoo_quotation(
        self,
        opportunity_id: uuid.UUID,
        payload: AttachOdooQuotationRequest,
    ) -> AttachOdooQuotationResponse:
        if not self.user_id:
            raise ValueError("Usuario requerido")

        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self.bid_svc._require_operational_interest(opportunity)

        pkg = await self.bid_svc._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")

        item, item_id = await self._resolve_economic_item(opportunity_id, payload.requirement_id)
        prev_status = item.get("status", "faltante")

        detail = await self.quotations.get_detail(payload.odoo_quotation_id)
        if not detail.connected or detail.message == "Cotización no encontrada o fuera de su empresa":
            raise ValueError("Cotización Odoo no encontrada o fuera del alcance de su empresa")

        pdf_bytes, _ = await self.quotations.download_pdf(payload.odoo_quotation_id)
        safe_code = opportunity.code.replace("/", "-").replace(" ", "_")
        filename = f"OFERTA_ECONOMICA_{safe_code}_{detail.name.replace('/', '-')}.pdf"

        storage = DGCPProcessStorageService(self.tenant_id)
        storage.write_bytes(opportunity.code, filename, pdf_bytes)

        now = datetime.now(timezone.utc)
        process_doc = DGCPProcessDocument(
            tenant_id=self.tenant_id,
            opportunity_id=opportunity_id,
            title=f"Oferta económica — {detail.name} ({detail.partner_name})",
            source_type="odoo_quotation",
            doc_role="checklist_evidence",
            priority="alta",
            format="pdf",
            ingestion_status="registered",
            metadata_={
                "storage_filename": filename,
                "storage_uri": storage.relative_uri(opportunity.code, filename),
                "requirement_key": ECONOMIC_OFFER_KEY,
                "checklist_item_id": str(item_id),
                "scope": "dgcp_process",
                "odoo_model": "sale.order",
                "odoo_id": payload.odoo_quotation_id,
                "odoo_name": detail.name,
                "customer": detail.partner_name,
                "amount_total": str(detail.amount_total),
                "currency": detail.currency,
                "downloaded_at": now.isoformat(),
                "downloaded_by": str(self.user_id),
                "source": "odoo",
            },
        )
        self.db.add(process_doc)
        await self.db.flush()

        checklist = self.bid_svc._deep_copy_checklist(pkg.checklist)
        target = next((i for i in checklist if str(i.get("id")) == str(item_id)), None)
        if not target:
            raise ValueError("Ítem de checklist no encontrado")

        target["process_document_id"] = str(process_doc.id)
        target["document_title"] = process_doc.title
        target["match_source"] = "odoo_quotation"
        target["relative_path"] = process_doc.metadata_.get("storage_uri")
        target["odoo_quotation_id"] = payload.odoo_quotation_id
        target["odoo_quotation_name"] = detail.name
        target["status"] = "adjuntado"
        target["display_status"] = self.compliance.display_status_label("adjuntado")
        target["notes"] = payload.notes or f"Cotización Odoo {detail.name} adjuntada al expediente"
        target["economic_offer_meta"] = {
            "odoo_model": "sale.order",
            "odoo_id": payload.odoo_quotation_id,
            "odoo_name": detail.name,
            "customer": detail.partner_name,
            "amount_total": str(detail.amount_total),
            "currency": detail.currency,
            "downloaded_at": now.isoformat(),
            "downloaded_by": str(self.user_id),
            "source": "odoo",
        }

        matches = [dict(m) for m in (pkg.document_matches or [])]
        for match in matches:
            if match.get("requirement_key") == ECONOMIC_OFFER_KEY:
                match.update({
                    "process_document_id": str(process_doc.id),
                    "document_title": process_doc.title,
                    "match_source": "odoo_quotation",
                    "relative_path": process_doc.metadata_.get("storage_uri"),
                    "status": "adjuntado",
                    "match_score": 98.0,
                    "notes": target["notes"],
                    "odoo_quotation_id": payload.odoo_quotation_id,
                })
                break
        else:
            matches.append({
                "requirement_key": ECONOMIC_OFFER_KEY,
                "requirement_label": "Oferta económica",
                "process_document_id": str(process_doc.id),
                "document_title": process_doc.title,
                "match_source": "odoo_quotation",
                "relative_path": process_doc.metadata_.get("storage_uri"),
                "status": "adjuntado",
                "match_score": 98.0,
                "odoo_quotation_id": payload.odoo_quotation_id,
            })

        bid = self.compliance.build_bid_package(opportunity, checklist, analyzed_at=pkg.analyzed_at)
        expediente_status = self.bid_svc._effective_expediente_status(
            opportunity, checklist, bid.preparation_pct, pkg
        )
        pkg.checklist = checklist
        pkg.document_matches = matches
        pkg.bid_package = bid.model_dump(mode="json")
        pkg.expediente_status = expediente_status

        draft = await self._upsert_draft(
            opportunity_id,
            item_id,
            customer_name=detail.partner_name,
            odoo_quotation_id=payload.odoo_quotation_id,
            odoo_quotation_name=detail.name,
            process_document_id=process_doc.id,
            status="attached",
            estimated_amount=detail.amount_total,
            currency=detail.currency,
        )
        draft.attached_at = now

        await self.audit.log(
            action="dgcp.economic_offer.attach_odoo_quotation",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="dgcp_bid_package",
            resource_id=pkg.id,
            details={
                "opportunity_id": str(opportunity_id),
                "checklist_item_id": str(item_id),
                "requirement_key": ECONOMIC_OFFER_KEY,
                "odoo_quotation_id": payload.odoo_quotation_id,
                "odoo_quotation_name": detail.name,
                "process_document_id": str(process_doc.id),
                "previous_status": prev_status,
                "new_status": "adjuntado",
                "preparation_pct": bid.preparation_pct,
            },
        )
        await self.audit.log(
            action="dgcp.economic_offer.pdf_downloaded",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="odoo_quotation",
            details={
                "odoo_quotation_id": payload.odoo_quotation_id,
                "filename": filename,
                "opportunity_id": str(opportunity_id),
            },
        )
        await self.db.commit()

        checklist_resp = self.bid_svc._checklist_response(opportunity_id, checklist)
        return AttachOdooQuotationResponse(
            opportunity_id=opportunity_id,
            checklist_item_id=item_id,
            requirement_key=ECONOMIC_OFFER_KEY,
            odoo_quotation_id=payload.odoo_quotation_id,
            odoo_quotation_name=detail.name,
            process_document_id=process_doc.id,
            document_title=process_doc.title,
            filename=filename,
            preparation_pct=bid.preparation_pct,
            expediente_status=expediente_status,
            economic_offer_status="adjuntado",
            draft_id=draft.id,
            checklist=checklist_resp,
            bid_package=bid,
        )

    async def create_draft_task(
        self,
        opportunity_id: uuid.UUID,
        payload: CreateEconomicOfferDraftTaskRequest,
    ) -> CreateEconomicOfferTaskResponse:
        if not self.user_id:
            raise ValueError("Usuario requerido")

        opportunity = await self._get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError("Licitación no encontrada")
        self.bid_svc._require_operational_interest(opportunity)

        pkg = await self.bid_svc._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")

        item, item_id = await self._resolve_economic_item(opportunity_id, payload.requirement_id)
        existing = await self._find_economic_offer_task(opportunity_id, item_id)
        if existing:
            return CreateEconomicOfferTaskResponse(
                task_id=existing.id,
                title=existing.title,
                created=False,
                existing=True,
                draft_id=(await self._get_draft(opportunity_id, item)).id
                if await self._get_draft(opportunity_id, item)
                else None,
            )

        suggested = payload.suggested_products or await self._suggest_products(opportunity)
        customer = payload.customer_name or opportunity.institution or "Cliente por definir"
        products_text = ""
        if suggested:
            products_text = "\n\nProductos sugeridos (Price Intelligence):\n" + "\n".join(
                f"- {p.product_name} | proveedor: {p.supplier or '—'} | "
                f"precio: {p.cost_price or '—'} {p.currency} | stock: {p.stock or '—'}"
                for p in suggested[:8]
            )

        description = (
            f"Preparar cotización económica para licitación DGCP {opportunity.code}.\n\n"
            f"Cliente/unidad de compra: {customer}\n"
            f"Objeto: {opportunity.title}\n"
            f"Fecha límite: {opportunity.deadline or 'Por confirmar'}\n"
            f"Enlace: /dgcp/{opportunity_id}\n"
            f"{payload.notes or ''}"
            f"{products_text}"
        ).strip()

        draft = await self._upsert_draft(
            opportunity_id,
            item_id,
            customer_name=customer,
            suggested_products=[p.model_dump(mode="json") for p in suggested],
            status="pending",
            assigned_to=payload.assigned_to,
            notes=payload.notes,
        )

        tasks = TaskService(self.db, self.tenant_id, user_id=self.user_id)
        task = await tasks.create_task(
            TaskCreateRequest(
                title=f"Preparar cotización económica para {opportunity.code}",
                description=description,
                category="cotizacion",
                department="comercial",
                priority="alta",
                source="dgcp_economic_offer",
                dgcp_process_id=opportunity_id,
                assigned_to_id=payload.assigned_to,
                due_date=opportunity.deadline,
                metadata={
                    "dgcp_opportunity_id": str(opportunity_id),
                    "dgcp_checklist_item_id": str(item_id),
                    "dgcp_requirement_key": ECONOMIC_OFFER_KEY,
                    "task_type": "economic_offer",
                    "economic_offer_draft_id": str(draft.id),
                },
                tags=["dgcp", "cotizacion", "oferta_economica"],
            )
        )
        draft.task_id = task.id
        draft.status = "in_progress"

        checklist = self.bid_svc._deep_copy_checklist(pkg.checklist)
        for ci in checklist:
            if str(ci.get("id")) == str(item_id):
                ci["task_id"] = str(task.id)
                if ci.get("status") == "faltante":
                    ci["status"] = "borrador_pendiente"
                    ci["display_status"] = self.compliance.display_status_label("borrador_pendiente")
                break
        pkg.checklist = checklist
        bid = self.compliance.build_bid_package(opportunity, checklist, analyzed_at=pkg.analyzed_at)
        pkg.bid_package = bid.model_dump(mode="json")

        await self.audit.log(
            action="dgcp.economic_offer.create_draft_task",
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="task",
            resource_id=task.id,
            details={
                "opportunity_id": str(opportunity_id),
                "checklist_item_id": str(item_id),
                "task_id": str(task.id),
                "draft_id": str(draft.id),
            },
        )
        await self.db.commit()

        return CreateEconomicOfferTaskResponse(
            task_id=task.id,
            title=task.title,
            created=True,
            existing=False,
            draft_id=draft.id,
        )

    async def _get_opportunity(self, opportunity_id: uuid.UUID) -> DGCPOpportunity | None:
        opp = await self.db.get(DGCPOpportunity, opportunity_id)
        if opp and opp.tenant_id == self.tenant_id:
            return opp
        return None

    async def _find_economic_offer_item(self, opportunity_id: uuid.UUID) -> dict | None:
        pkg = await self.bid_svc._get_package(opportunity_id)
        if not pkg:
            return None
        for item in pkg.checklist or []:
            if item.get("requirement_key") == ECONOMIC_OFFER_KEY:
                return item
        return None

    async def _resolve_economic_item(
        self,
        opportunity_id: uuid.UUID,
        requirement_id: uuid.UUID | None,
    ) -> tuple[dict, uuid.UUID]:
        pkg = await self.bid_svc._get_package(opportunity_id)
        if not pkg:
            raise ValueError("Ejecute el análisis de requisitos primero")
        checklist = pkg.checklist or []
        if requirement_id:
            for item in checklist:
                if str(item.get("id")) == str(requirement_id):
                    return item, uuid.UUID(str(item["id"]))
            raise ValueError("Requisito no encontrado en checklist")
        for item in checklist:
            if item.get("requirement_key") == ECONOMIC_OFFER_KEY:
                return item, uuid.UUID(str(item["id"]))
        raise ValueError("Requisito Oferta económica no encontrado — ejecute análisis")

    async def _find_economic_offer_task(
        self,
        opportunity_id: uuid.UUID,
        checklist_item_id: uuid.UUID,
    ) -> Task | None:
        result = await self.db.execute(
            select(Task).where(
                Task.tenant_id == self.tenant_id,
                Task.dgcp_process_id == opportunity_id,
                Task.status.in_(tuple(ACTIVE_TASK_STATUSES)),
            )
        )
        for task in result.scalars().all():
            meta = task.metadata_ or {}
            if meta.get("task_type") == "economic_offer" and meta.get("dgcp_checklist_item_id") == str(checklist_item_id):
                return task
        return None

    async def _get_draft(
        self,
        opportunity_id: uuid.UUID,
        item: dict | None,
    ) -> EconomicOfferDraft | None:
        req_id = uuid.UUID(str(item["id"])) if item and item.get("id") else None
        q = select(EconomicOfferDraft).where(
            EconomicOfferDraft.tenant_id == self.tenant_id,
            EconomicOfferDraft.opportunity_id == opportunity_id,
        )
        if req_id:
            q = q.where(EconomicOfferDraft.requirement_id == req_id)
        result = await self.db.execute(q.limit(1))
        return result.scalar_one_or_none()

    async def _upsert_draft(
        self,
        opportunity_id: uuid.UUID,
        requirement_id: uuid.UUID,
        **fields,
    ) -> EconomicOfferDraft:
        draft = await self._get_draft(opportunity_id, {"id": str(requirement_id)})
        if not draft:
            draft = EconomicOfferDraft(
                tenant_id=self.tenant_id,
                opportunity_id=opportunity_id,
                requirement_id=requirement_id,
                user_id=self.user_id,
            )
            self.db.add(draft)
        for key, value in fields.items():
            if hasattr(draft, key):
                setattr(draft, key, value)
        await self.db.flush()
        return draft

    async def _suggest_products(self, opportunity: DGCPOpportunity) -> list[EconomicOfferSuggestedProduct]:
        terms: list[str] = []
        title = (opportunity.title or "").lower()
        for token in title.split():
            if len(token) >= 4:
                terms.append(token)
        if not terms:
            return []

        price_svc = PriceIntelligenceService(self.db, self.tenant_id)
        suggestions: list[EconomicOfferSuggestedProduct] = []
        seen: set[str] = set()
        for term in terms[:3]:
            try:
                from app.services.price_intelligence_service import PriceSearchFilters

                result = await price_svc.search(PriceSearchFilters(q=term, limit=5))
                for item in result.items:
                    key = item.description or item.sku or ""
                    if key in seen:
                        continue
                    seen.add(key)
                    suggestions.append(
                        EconomicOfferSuggestedProduct(
                            product_name=item.description or item.sku or term,
                            supplier=item.supplier,
                            cost_price=item.preferred_price or item.price,
                            currency=item.currency or "USD",
                            stock=float(item.stock) if item.stock is not None else None,
                            source=item.source_filename,
                            source_date=item.source_file_date.isoformat() if item.source_file_date else None,
                            price_product_id=item.id,
                        )
                    )
            except Exception:
                continue
        return suggestions[:10]

    @staticmethod
    def _has_evidence(item: dict) -> bool:
        return bool(
            item.get("process_document_id")
            or item.get("document_id")
            or item.get("knowledge_asset_id")
        )
