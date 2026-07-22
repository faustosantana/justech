"""Enlaces compartibles seguros — snapshot inmutable, token hasheado."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import forbidden, not_found
from app.models.lottery import LotteryAuditLog, LotterySharedQuery
from app.schemas.lottery_share import (
    LotteryShareCreateRequest,
    LotteryShareListResponse,
    LotteryShareResponse,
    LotterySharedViewResponse,
)
from app.services.lottery_exceptions import LotteryQueryError
from app.services.lottery_export_service import LotteryExportService
from app.services.lottery_product_service import DISCLAIMER


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _status(row: LotterySharedQuery, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    if row.revoked_at is not None:
        return "revoked"
    if row.expires_at <= now:
        return "expired"
    if row.max_views is not None and row.view_count >= row.max_views:
        return "max_views"
    return "active"


def _sanitize_title(title: str) -> str:
    # Evitar XSS trivial en títulos; el FE escapa, pero limitamos caracteres de control.
    cleaned = "".join(ch for ch in title if ch.isprintable())
    return cleaned.strip()[:255] or "Consulta compartida"


class LotteryShareService:
    def __init__(self, db: AsyncSession, *, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def create(self, req: LotteryShareCreateRequest) -> LotteryShareResponse:
        title = _sanitize_title(req.title)
        ttl = min(req.ttl_hours, settings.lottery_share_max_ttl_hours)
        expires = datetime.now(timezone.utc) + timedelta(hours=ttl)

        # Snapshot inmutable: reutiliza recolector de exports sin escribir archivo.
        exporter = LotteryExportService(self.db, tenant_id=self.tenant_id, user_id=self.user_id)
        from app.schemas.lottery_product import LotteryExportRequest

        rows, meta = await exporter._collect_rows(
            LotteryExportRequest(
                query_type=req.query_type,
                query_parameters=req.query_parameters,
                format="csv",
                title=title,
            )
        )
        # Limitar snapshot
        if len(rows) > 500:
            raise LotteryQueryError(
                "RANGE_TOO_LARGE",
                "El snapshot de share admite máximo 500 filas. Reduce el rango.",
                details={"row_count": len(rows), "limit": 500},
            )

        token = secrets.token_urlsafe(32)
        row = LotterySharedQuery(
            tenant_id=self.tenant_id,
            created_by_user_id=self.user_id,
            token_hash=_hash_token(token),
            query_type=req.query_type,
            query_parameters=dict(req.query_parameters),
            snapshot={
                "meta": {k: v for k, v in meta.items() if k != "raw"},
                "rows": rows,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            title=title,
            expires_at=expires,
            max_views=req.max_views,
            allow_export=bool(req.allow_export),
            view_count=0,
        )
        self.db.add(row)
        self.db.add(
            LotteryAuditLog(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                action="share_create",
                tool_name="lottery_share",
                parameters={
                    "query_type": req.query_type,
                    "ttl_hours": ttl,
                    "max_views": req.max_views,
                    "rows": len(rows),
                    # nunca el token
                },
                result_count=len(rows),
            )
        )
        await self.db.flush()
        return LotteryShareResponse(
            share_id=row.id,
            title=row.title,
            query_type=row.query_type,
            expires_at=row.expires_at,
            max_views=row.max_views,
            view_count=0,
            allow_export=row.allow_export,
            status="active",
            share_url=f"/lottery/shared/{token}",
            token=token,
            created_at=row.created_at,
        )

    async def list_mine(self) -> LotteryShareListResponse:
        q = await self.db.execute(
            select(LotterySharedQuery)
            .where(
                LotterySharedQuery.tenant_id == self.tenant_id,
                LotterySharedQuery.created_by_user_id == self.user_id,
            )
            .order_by(LotterySharedQuery.created_at.desc())
            .limit(100)
        )
        items = [
            LotteryShareResponse(
                share_id=r.id,
                title=r.title,
                query_type=r.query_type,
                expires_at=r.expires_at,
                revoked_at=r.revoked_at,
                max_views=r.max_views,
                view_count=r.view_count,
                allow_export=r.allow_export,
                status=_status(r),
                created_at=r.created_at,
            )
            for r in q.scalars().all()
        ]
        return LotteryShareListResponse(items=items, total=len(items))

    async def get_mine(self, share_id: uuid.UUID) -> LotteryShareResponse:
        row = await self._get_owned(share_id)
        return LotteryShareResponse(
            share_id=row.id,
            title=row.title,
            query_type=row.query_type,
            expires_at=row.expires_at,
            revoked_at=row.revoked_at,
            max_views=row.max_views,
            view_count=row.view_count,
            allow_export=row.allow_export,
            status=_status(row),
            created_at=row.created_at,
        )

    async def revoke(self, share_id: uuid.UUID) -> LotteryShareResponse:
        row = await self._get_owned(share_id)
        row.revoked_at = datetime.now(timezone.utc)
        await self.db.flush()
        self.db.add(
            LotteryAuditLog(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                action="share_revoke",
                tool_name="lottery_share",
                parameters={"share_id": str(share_id)},
            )
        )
        await self.db.flush()
        return await self.get_mine(share_id)

    async def delete(self, share_id: uuid.UUID) -> None:
        from sqlalchemy import delete as sa_delete

        row = await self._get_owned(share_id)
        await self.db.execute(sa_delete(LotterySharedQuery).where(LotterySharedQuery.id == row.id))
        await self.db.flush()

    async def _get_owned(self, share_id: uuid.UUID) -> LotterySharedQuery:
        row = await self.db.get(LotterySharedQuery, share_id)
        if not row or row.tenant_id != self.tenant_id or row.created_by_user_id != self.user_id:
            raise not_found("Share no encontrado")
        return row


async def view_shared_by_token(db: AsyncSession, token: str) -> LotterySharedViewResponse:
    """Vista pública limitada — sin tenant/user/navegación JAIOS."""
    if not token or len(token) < 20 or len(token) > 128:
        raise not_found("Enlace no válido")
    token_hash = _hash_token(token)
    q = await db.execute(select(LotterySharedQuery).where(LotterySharedQuery.token_hash == token_hash))
    row = q.scalar_one_or_none()
    if not row:
        # comparación constante-ish para no filtrar existencia por timing trivial
        _ = hmac.compare_digest(token_hash, "0" * 64)
        raise not_found("Enlace no válido o expirado")

    status = _status(row)
    if status != "active":
        raise forbidden(f"Enlace no disponible ({status})")

    row.view_count = int(row.view_count or 0) + 1
    row.last_viewed_at = datetime.now(timezone.utc)
    await db.flush()

    # Re-check max_views after increment
    if row.max_views is not None and row.view_count > row.max_views:
        raise forbidden("Enlace no disponible (max_views)")

    snap = dict(row.snapshot or {})
    generated = snap.get("generated_at")
    gen_dt = None
    if generated:
        try:
            gen_dt = datetime.fromisoformat(str(generated).replace("Z", "+00:00"))
        except ValueError:
            gen_dt = None

    # No exponer tenant_id / user_id / query_parameters completos sensibles
    result: dict[str, Any] = {
        "rows": snap.get("rows") or [],
        "meta": {
            k: v
            for k, v in (snap.get("meta") or {}).items()
            if k in ("query_type", "filters", "resolved_lottery", "from_date", "to_date", "date")
        },
    }

    return LotterySharedViewResponse(
        title=row.title,
        query_type=row.query_type,
        generated_at=gen_dt,
        expires_at=row.expires_at,
        disclaimer=DISCLAIMER,
        result=result,
        allow_export=bool(row.allow_export),
    )
