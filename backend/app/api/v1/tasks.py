import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentUser, DbSession, TenantCtx
from app.core.tenant import require_tenant_context
from app.schemas.tasks import (
    TaskChecklistCreateRequest,
    TaskChecklistUpdateRequest,
    TaskCommentCreateRequest,
    TaskCreateRequest,
    TaskFromEventRequest,
    TaskListResponse,
    TaskResponse,
    TaskUpdateRequest,
)
from app.services.task_service import TaskService
from app.schemas.bulk_actions import BulkActionResult, TaskBulkRequest
from app.services.bulk_actions_service import BulkActionsService

router = APIRouter(prefix="/tasks", tags=["Tasks Center"])


def _svc(db: DbSession, user: CurrentUser) -> TaskService:
    ctx = require_tenant_context()
    return TaskService(db, ctx.tenant_id, user_id=user.id)


def _bulk(db: DbSession, user: CurrentUser) -> BulkActionsService:
    ctx = require_tenant_context()
    return BulkActionsService(db, ctx.tenant_id, user.id)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    status: Annotated[str | None, Query()] = None,
    priority: Annotated[str | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
    department: Annotated[str | None, Query()] = None,
    assigned_to_id: Annotated[uuid.UUID | None, Query()] = None,
    search: Annotated[str, Query()] = "",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaskListResponse:
    return await _svc(db, user).list_tasks(
        status=status,
        priority=priority,
        category=category,
        department=department,
        assigned_to_id=assigned_to_id,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    db: DbSession, user: CurrentUser, _: TenantCtx, payload: TaskCreateRequest
) -> TaskResponse:
    return await _svc(db, user).create_task(payload)


@router.post("/from-event", response_model=TaskResponse, status_code=201)
async def create_task_from_event(
    db: DbSession, user: CurrentUser, _: TenantCtx, payload: TaskFromEventRequest
) -> TaskResponse:
    return await _svc(db, user).create_from_event(payload)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    db: DbSession, user: CurrentUser, _: TenantCtx, task_id: uuid.UUID
) -> TaskResponse:
    task = await _svc(db, user).get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    task_id: uuid.UUID,
    payload: TaskUpdateRequest,
) -> TaskResponse:
    task = await _svc(db, user).update_task(task_id, payload)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    db: DbSession, user: CurrentUser, _: TenantCtx, task_id: uuid.UUID
) -> None:
    if not await _svc(db, user).delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/{task_id}/comments", response_model=TaskResponse)
async def add_comment(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    task_id: uuid.UUID,
    payload: TaskCommentCreateRequest,
) -> TaskResponse:
    task = await _svc(db, user).add_comment(task_id, payload.comment)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/checklist", response_model=TaskResponse)
async def add_checklist_item(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    task_id: uuid.UUID,
    payload: TaskChecklistCreateRequest,
) -> TaskResponse:
    task = await _svc(db, user).add_checklist_item(task_id, payload.text)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}/checklist/{item_id}", response_model=TaskResponse)
async def update_checklist_item(
    db: DbSession,
    user: CurrentUser,
    _: TenantCtx,
    task_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: TaskChecklistUpdateRequest,
) -> TaskResponse:
    task = await _svc(db, user).update_checklist_item(task_id, item_id, payload.completed)
    if not task:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    return task


@router.post("/bulk", response_model=BulkActionResult)
async def tasks_bulk(
    db: DbSession, user: CurrentUser, _: TenantCtx, payload: TaskBulkRequest
) -> BulkActionResult:
    return await _bulk(db, user).tasks_bulk(
        payload.ids,
        payload.action,
        status=payload.status,
        priority=payload.priority,
        assigned_to_id=payload.assigned_to_id,
    )
