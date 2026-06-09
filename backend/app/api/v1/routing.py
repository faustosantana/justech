from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.routing import RoutingApplyRequest, RoutingPreviewRequest, RoutingPreviewResponse
from app.schemas.tasks import TaskFromEventRequest, TaskResponse
from app.services.routing_service import RoutingService
from app.services.task_service import TaskService

router = APIRouter(prefix="/routing", tags=["Operational Routing"])


@router.post("/preview", response_model=RoutingPreviewResponse)
async def routing_preview(
    db: DbSession, user: CurrentUser, _: TenantCtx, payload: RoutingPreviewRequest
) -> RoutingPreviewResponse:
    ctx = require_tenant_context()
    return await RoutingService(db, ctx.tenant_id).preview(
        event_type=payload.event_type,
        title=payload.title,
        description=payload.description,
        customer_name=payload.customer_name,
        amount=payload.amount,
        metadata=payload.metadata,
    )


@router.post("/apply", response_model=TaskResponse, status_code=201)
async def routing_apply(
    db: DbSession, user: CurrentUser, _: TenantCtx, payload: RoutingApplyRequest
) -> TaskResponse:
    ctx = require_tenant_context()
    svc = TaskService(db, ctx.tenant_id, user_id=user.id)
    dgcp_id = None
    if payload.dgcp_process_id:
        import uuid as _uuid
        try:
            dgcp_id = _uuid.UUID(payload.dgcp_process_id)
        except ValueError:
            dgcp_id = None
    return await svc.create_from_event(
        TaskFromEventRequest(
            source=payload.source,
            event_type=payload.event_type,
            title=payload.title,
            description=payload.description,
            customer_name=payload.customer_name,
            amount=payload.amount,
            related_entity_type=payload.related_entity_type,
            related_entity_id=payload.related_entity_id,
            odoo_customer_id=payload.odoo_customer_id,
            odoo_invoice_id=payload.odoo_invoice_id,
            odoo_quotation_id=payload.odoo_quotation_id,
            dgcp_process_id=dgcp_id,
            metadata=payload.metadata,
            apply_routing=True,
        )
    )
