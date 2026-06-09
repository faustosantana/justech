"""Borradores internos de cotización desde Price Intelligence."""

from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_list import PriceListProduct, PriceQuoteDraft
from app.models.work_enums import NotificationType, TaskCategory, TaskDepartment, TaskSource
from app.schemas.prices import (
    OdooProductMatchResponse,
    PriceQuoteDraftCreate,
    PriceQuoteDraftListResponse,
    PriceQuoteDraftResponse,
)
from app.schemas.tasks import TaskCreateRequest
from app.services.notification_service import NotificationService
from app.services.odoo_service import OdooService
from app.services.price_intelligence_service import PriceIntelligenceService
from app.services.task_service import TaskService


DEFAULT_MARGIN = Decimal("15")
DRAFT_STATUS_PENDING = "pendiente_revision_vendedor"


class PriceQuoteDraftService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.prices = PriceIntelligenceService(db, tenant_id)

    async def create_draft(self, payload: PriceQuoteDraftCreate) -> PriceQuoteDraftResponse:
        product = await self.prices.get_product(payload.product_id)
        if not product:
            raise ValueError("Producto no encontrado")
        if not product.is_cotizable:
            raise ValueError(
                "Este producto no es cotizable como línea principal "
                f"({product.classification_label}). Revise la clasificación."
            )

        margin = payload.margin_percent if payload.margin_percent is not None else DEFAULT_MARGIN
        cost = product.preferred_price or product.price
        sale = None
        if cost is not None:
            sale = (cost * (Decimal("1") + margin / Decimal("100"))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        draft = PriceQuoteDraft(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            product_id=payload.product_id,
            client_name=payload.client_name,
            quantity=payload.quantity,
            description=product.description,
            cost_price=cost,
            currency=product.currency,
            supplier=product.supplier,
            margin_percent=margin,
            sale_price_suggested=sale,
            source_filename=product.source_filename,
            source_sheet=product.source_sheet,
            source_row=product.source_row,
            source_file_date=product.source_file_date,
            status=DRAFT_STATUS_PENDING,
            metadata_={
                "preferred_price_field": product.preferred_price_field,
                "prices_original": product.prices_original,
                "sku": product.sku,
                "mpn": product.mpn,
                "classification_label": product.classification_label,
            },
        )
        self.db.add(draft)
        await self.db.flush()

        task_svc = TaskService(self.db, self.tenant_id, user_id=self.user_id)
        title = f"Cotización: {(product.description or product.sku or 'producto')[:120]}"
        task = await task_svc.create_task(
            TaskCreateRequest(
                title=title,
                description=(
                    f"Revisar borrador de cotización desde Price Intelligence.\n"
                    f"Cliente: {payload.client_name or '—'}\n"
                    f"Costo: {product.currency} {cost}\n"
                    f"Venta sugerida ({margin}%): {product.currency} {sale}\n"
                    f"Fuente: {product.source_filename} / {product.source_sheet} fila {product.source_row}"
                ),
                category=TaskCategory.COTIZACION.value,
                department=TaskDepartment.VENTAS.value,
                priority="media",
                source=TaskSource.PRICE_INTELLIGENCE.value,
                customer_name=payload.client_name,
                amount=sale,
                currency=product.currency,
                suggested_assignee_name="Marieli",
                metadata={
                    "price_quote_draft_id": str(draft.id),
                    "product_id": str(product.id),
                    "source_filename": product.source_filename,
                    "source_sheet": product.source_sheet,
                    "source_row": product.source_row,
                },
                checklist=[
                    "Verificar precio vs Excel",
                    "Confirmar stock con proveedor",
                    "Buscar producto en Odoo",
                    "Preparar cotización final",
                ],
            )
        )
        draft.task_id = task.id
        draft.metadata_ = {**draft.metadata_, "task_id": str(task.id)}

        if self.user_id:
            notifications = NotificationService(self.db, self.tenant_id)
            await notifications.create(
                user_id=self.user_id,
                title="Revisar borrador de cotización",
                message=f"Se creó borrador para {product.description or product.sku}. Tarea: {task.title}",
                type=NotificationType.QUOTATION_FOLLOWUP.value,
                related_task_id=task.id,
                related_entity_type="price_quote_draft",
                related_entity_id=str(draft.id),
            )

        await self.db.commit()
        await self.db.refresh(draft)
        return self._to_response(draft, product, task_id=task.id)

    async def list_drafts(self, *, limit: int = 50, offset: int = 0) -> PriceQuoteDraftListResponse:
        from app.models.task import Task
        from app.services.company_scope_filter import CompanyScopeFilter

        base = select(PriceQuoteDraft).where(PriceQuoteDraft.tenant_id == self.tenant_id)
        if self.user_id:
            clause = await CompanyScopeFilter(
                self.db, self.tenant_id, self.user_id
            ).task_company_clause(Task.company_id)
            if clause is not None:
                base = base.outerjoin(Task, PriceQuoteDraft.task_id == Task.id).where(
                    or_(PriceQuoteDraft.task_id.is_(None), clause)
                )
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()
        rows = (
            await self.db.execute(
                base.order_by(PriceQuoteDraft.created_at.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()
        items = []
        for draft in rows:
            product = await self.prices.get_product(draft.product_id)
            items.append(self._to_response(draft, product, task_id=draft.task_id))
        return PriceQuoteDraftListResponse(items=items, total=total)

    async def odoo_match(self, product_id: uuid.UUID) -> OdooProductMatchResponse:
        product = await self.prices.get_product(product_id)
        if not product:
            return OdooProductMatchResponse(
                found=False,
                message="Producto no encontrado en Price Intelligence.",
                action="none",
            )

        odoo = OdooService(self.db, self.tenant_id)
        search_terms = [t for t in (product.sku, product.mpn, product.model) if t]
        if product.description:
            search_terms.append(product.description[:80])

        for term in search_terms:
            result = await odoo.list_products(search=term, limit=5)
            if result.items:
                match = result.items[0]
                return OdooProductMatchResponse(
                    found=True,
                    product_id=match.id,
                    product_name=match.name,
                    message=f"Producto encontrado en Odoo: {match.name}",
                    action="open_odoo_product",
                    odoo_default_code=match.default_code,
                )

        return OdooProductMatchResponse(
            found=False,
            message=(
                "Producto no existe en Odoo (búsqueda por SKU/MPN/modelo). "
                "Puede crear tarea para registrar producto."
            ),
            action="create_product_task",
        )

    def _to_response(self, draft: PriceQuoteDraft, product, *, task_id: uuid.UUID | None = None) -> PriceQuoteDraftResponse:
        desc = product.description if product else draft.description
        copy_line = (
            f"{desc or draft.metadata_.get('sku')} | "
            f"Costo: {draft.currency} {draft.cost_price} | "
            f"Venta sugerida ({draft.margin_percent}%): {draft.currency} {draft.sale_price_suggested} | "
            f"Proveedor: {draft.supplier} | Fuente: {draft.source_filename} ({draft.source_sheet} fila {draft.source_row})"
        )
        return PriceQuoteDraftResponse(
            id=draft.id,
            product_id=draft.product_id,
            task_id=task_id or draft.task_id,
            client_name=draft.client_name,
            quantity=draft.quantity,
            description=draft.description,
            cost_price=draft.cost_price,
            currency=draft.currency,
            supplier=draft.supplier,
            margin_percent=draft.margin_percent,
            sale_price_suggested=draft.sale_price_suggested,
            source_filename=draft.source_filename,
            source_sheet=draft.source_sheet,
            source_row=draft.source_row,
            source_file_date=draft.source_file_date,
            status=draft.status,
            odoo_product_id=draft.odoo_product_id,
            odoo_match_status=draft.odoo_match_status,
            user_id=draft.user_id,
            copy_line=copy_line,
        )
