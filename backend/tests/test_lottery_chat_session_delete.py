"""Ownership and bulk delete for lottery chat sessions."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.lottery import LotteryChatSession
from app.services.lottery_chat_service import LotteryChatService


def _svc(tenant_id: uuid.UUID, user_id: uuid.UUID) -> LotteryChatService:
    db = AsyncMock()
    return LotteryChatService(db, tenant_id=tenant_id, user_id=user_id)


def _session(
    *,
    sid: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> LotteryChatSession:
    s = MagicMock(spec=LotteryChatSession)
    s.id = sid
    s.tenant_id = tenant_id
    s.user_id = user_id
    return s


@pytest.mark.asyncio
async def test_delete_session_forbidden_other_user():
    tenant = uuid.uuid4()
    owner = uuid.uuid4()
    other = uuid.uuid4()
    sid = uuid.uuid4()
    svc = _svc(tenant, other)
    svc.db.get = AsyncMock(return_value=_session(sid=sid, tenant_id=tenant, user_id=owner))
    with pytest.raises(HTTPException) as exc:
        await svc.delete_session(sid)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_session_not_found():
    svc = _svc(uuid.uuid4(), uuid.uuid4())
    svc.db.get = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as exc:
        await svc.delete_session(uuid.uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_bulk_delete_owned_and_failed():
    tenant = uuid.uuid4()
    user = uuid.uuid4()
    owned_id = uuid.uuid4()
    foreign_id = uuid.uuid4()
    missing_id = uuid.uuid4()
    svc = _svc(tenant, user)

    owned = _session(sid=owned_id, tenant_id=tenant, user_id=user)
    foreign = _session(sid=foreign_id, tenant_id=tenant, user_id=uuid.uuid4())

    async def _get(_model, sid):
        if sid == owned_id:
            return owned
        if sid == foreign_id:
            return foreign
        return None

    svc.db.get = AsyncMock(side_effect=_get)
    svc.db.delete = AsyncMock()
    svc.db.flush = AsyncMock()

    result = await svc.bulk_delete_sessions([owned_id, foreign_id, missing_id, owned_id])
    assert result["deleted_count"] == 1
    assert set(result["failed_ids"]) == {str(foreign_id), str(missing_id)}
    assert result["success"] is False
    svc.db.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_all_only_current_user():
    tenant = uuid.uuid4()
    user = uuid.uuid4()
    svc = _svc(tenant, user)
    a = _session(sid=uuid.uuid4(), tenant_id=tenant, user_id=user)
    b = _session(sid=uuid.uuid4(), tenant_id=tenant, user_id=user)

    result_proxy = MagicMock()
    result_proxy.scalars.return_value.all.return_value = [a, b]
    svc.db.execute = AsyncMock(return_value=result_proxy)
    svc.db.delete = AsyncMock()
    svc.db.flush = AsyncMock()

    result = await svc.delete_all_sessions()
    assert result["deleted_count"] == 2
    assert result["failed_ids"] == []
    assert result["success"] is True
    assert svc.db.delete.await_count == 2
