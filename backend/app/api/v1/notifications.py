import uuid

from fastapi import APIRouter, HTTPException
from typing import Annotated

from fastapi import Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.notifications import NotificationListResponse, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications Center"])


def _svc(db: DbSession, user: CurrentUser) -> NotificationService:
    ctx = require_tenant_context()
    return NotificationService(db, ctx.tenant_id, user_id=user.id)


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    unread_only: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> NotificationListResponse:
    return await _svc(db, user).list_for_user(user.id, unread_only=unread_only, limit=limit)


@router.get("/unread-count")
async def unread_count(db: DbSession, user: CurrentUser, _: TenantCtx) -> dict:
    count = await _svc(db, user).unread_count(user.id)
    return {"unread_count": count}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    db: DbSession, user: CurrentUser, _: TenantCtx, notification_id: uuid.UUID
) -> NotificationResponse:
    notif = await _svc(db, user).mark_read(notification_id, user.id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationResponse.model_validate(notif)


@router.post("/read-all")
async def mark_all_read(db: DbSession, user: CurrentUser, _: TenantCtx) -> dict:
    count = await _svc(db, user).mark_all_read(user.id)
    return {"marked_read": count}
