from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.odoo_context import OdooUserMapping, UserCompanyContext
from app.services.audit_service import AuditService
from app.schemas.odoo import (
    OdooCompaniesResponse,
    OdooCompanyContextResponse,
    OdooCompanyContextUpdate,
    OdooCompanyResponse,
    OdooLinkUserRequest,
    OdooMeResponse,
    OdooUserMappingResponse,
)
from integrations.odoo.company_context import OdooCompanyContext
from integrations.odoo.exceptions import OdooNotConfiguredError
from integrations.odoo.normalize import (
    odoo_bool,
    odoo_m2m_ids,
    odoo_m2o_id,
    odoo_m2o_name_opt,
    odoo_str,
)


class OdooCompanyContextService:
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        odoo_client_factory,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._odoo_client_factory = odoo_client_factory

    async def _client(self):
        return await self._odoo_client_factory()

    async def get_active_odoo_context(self) -> OdooCompanyContext | None:
        result = await self.db.execute(
            select(UserCompanyContext).where(
                UserCompanyContext.tenant_id == self.tenant_id,
                UserCompanyContext.jaios_user_id == self.user_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        mapping = await self._get_user_mapping()
        allowed = tuple(mapping.allowed_company_ids) if mapping and mapping.allowed_company_ids else (row.odoo_company_id,)
        if row.odoo_company_id not in allowed and mapping and mapping.allowed_company_ids:
            allowed = (row.odoo_company_id,)
        return OdooCompanyContext(company_id=row.odoo_company_id, allowed_company_ids=allowed)

    async def get_context_response(self) -> OdooCompanyContextResponse:
        result = await self.db.execute(
            select(UserCompanyContext).where(
                UserCompanyContext.tenant_id == self.tenant_id,
                UserCompanyContext.jaios_user_id == self.user_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            return OdooCompanyContextResponse(selected=False)
        return OdooCompanyContextResponse(
            selected=True,
            odoo_company_id=row.odoo_company_id,
            odoo_company_name=row.odoo_company_name,
            is_default=row.is_default,
            selected_at=row.selected_at,
        )

    async def set_context(self, payload: OdooCompanyContextUpdate) -> OdooCompanyContextResponse:
        companies = await self.list_companies()
        if not companies.connected:
            return OdooCompanyContextResponse(selected=False, message="Odoo no conectado")
        match = next((c for c in companies.items if c.id == payload.odoo_company_id), None)
        if not match:
            from app.core.exceptions import JAIOSException

            raise JAIOSException("Empresa Odoo no encontrada", code="ODOO_COMPANY_NOT_FOUND")

        mapping = await self._get_user_mapping()
        if mapping and mapping.allowed_company_ids:
            if payload.odoo_company_id not in mapping.allowed_company_ids:
                from app.core.exceptions import JAIOSException

                raise JAIOSException(
                    "Empresa no permitida para tu usuario Odoo",
                    code="ODOO_COMPANY_NOT_ALLOWED",
                )

        result = await self.db.execute(
            select(UserCompanyContext).where(
                UserCompanyContext.tenant_id == self.tenant_id,
                UserCompanyContext.jaios_user_id == self.user_id,
            )
        )
        row = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if row:
            row.odoo_company_id = payload.odoo_company_id
            row.odoo_company_name = match.name
            row.is_default = True
            row.selected_at = now
        else:
            row = UserCompanyContext(
                tenant_id=self.tenant_id,
                jaios_user_id=self.user_id,
                odoo_company_id=payload.odoo_company_id,
                odoo_company_name=match.name,
                is_default=True,
                selected_at=now,
            )
            self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return OdooCompanyContextResponse(
            selected=True,
            odoo_company_id=row.odoo_company_id,
            odoo_company_name=row.odoo_company_name,
            is_default=row.is_default,
            selected_at=row.selected_at,
        )

    async def list_companies(self) -> OdooCompaniesResponse:
        client = await self._client()
        if not client.is_configured:
            return OdooCompaniesResponse(
                items=[],
                connected=False,
                message="Odoo no conectado",
            )
        try:
            rows = await client.search_read(
                "res.company",
                [],
                ["name", "currency_id", "partner_id", "active"],
                limit=100,
                order="name asc",
            )
        except OdooNotConfiguredError:
            return OdooCompaniesResponse(items=[], connected=False, message="Odoo no conectado")

        selected_id = None
        ctx_result = await self.db.execute(
            select(UserCompanyContext).where(
                UserCompanyContext.tenant_id == self.tenant_id,
                UserCompanyContext.jaios_user_id == self.user_id,
            )
        )
        ctx_row = ctx_result.scalar_one_or_none()
        if ctx_row:
            selected_id = ctx_row.odoo_company_id

        mapping = await self._get_user_mapping()
        allowed_ids: set[int] | None = None
        if mapping and mapping.allowed_company_ids:
            allowed_ids = set(mapping.allowed_company_ids)

        items = [
            OdooCompanyResponse(
                id=r["id"],
                name=odoo_str(r.get("name")),
                currency_id=odoo_m2o_id(r.get("currency_id")),
                currency_name=odoo_m2o_name_opt(r.get("currency_id")),
                partner_id=odoo_m2o_id(r.get("partner_id")),
                is_active=odoo_bool(r.get("active"), default=True),
                selected_by_current_user=r["id"] == selected_id,
            )
            for r in rows
            if allowed_ids is None or r["id"] in allowed_ids
        ]
        return OdooCompaniesResponse(items=items, connected=True)

    async def _get_user_mapping(self) -> OdooUserMapping | None:
        result = await self.db.execute(
            select(OdooUserMapping).where(
                OdooUserMapping.tenant_id == self.tenant_id,
                OdooUserMapping.jaios_user_id == self.user_id,
                OdooUserMapping.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _audit(self, action: str, details: dict) -> None:
        audit = AuditService(self.db)
        await audit.log(
            action=action,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="odoo_user_mapping",
            details=details,
        )
        await self.db.commit()

    async def link_user(self, payload: OdooLinkUserRequest) -> OdooUserMappingResponse:
        from app.core.exceptions import JAIOSException

        client = await self._client()
        if not client.is_configured:
            await self._audit(
                "odoo.user_link_failed",
                {"reason": "not_connected", "odoo_login": payload.odoo_login},
            )
            raise JAIOSException("Odoo no conectado", code="ODOO_NOT_CONNECTED")

        domain: list = [("login", "=", payload.odoo_login)]
        users = await client.search_read(
            "res.users",
            domain,
            ["id", "login", "partner_id", "company_id", "company_ids"],
            limit=1,
        )
        if not users:
            await self._audit(
                "odoo.user_link_failed",
                {"reason": "user_not_found", "odoo_login": payload.odoo_login},
            )
            raise JAIOSException(
                f"Usuario Odoo no encontrado: {payload.odoo_login}",
                code="ODOO_USER_NOT_FOUND",
            )

        odoo_user = users[0]
        company_ids = odoo_m2m_ids(odoo_user.get("company_ids"))
        if not company_ids and odoo_user.get("company_id"):
            cid = odoo_m2o_id(odoo_user.get("company_id"))
            if cid:
                company_ids = [cid]

        result = await self.db.execute(
            select(OdooUserMapping).where(
                OdooUserMapping.tenant_id == self.tenant_id,
                OdooUserMapping.jaios_user_id == self.user_id,
            )
        )
        row = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        default_company = odoo_m2o_id(odoo_user.get("company_id"))
        if row:
            row.odoo_user_id = odoo_user["id"]
            row.odoo_login = odoo_str(odoo_user.get("login")) or payload.odoo_login
            row.odoo_partner_id = odoo_m2o_id(odoo_user.get("partner_id"))
            row.allowed_company_ids = list(company_ids)
            row.default_company_id = default_company
            row.is_active = True
            row.last_verified_at = now
        else:
            row = OdooUserMapping(
                tenant_id=self.tenant_id,
                jaios_user_id=self.user_id,
                odoo_user_id=odoo_user["id"],
                odoo_login=odoo_str(odoo_user.get("login")) or payload.odoo_login,
                odoo_partner_id=odoo_m2o_id(odoo_user.get("partner_id")),
                allowed_company_ids=list(company_ids),
                default_company_id=default_company,
                is_active=True,
                last_verified_at=now,
            )
            self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        await self._audit(
            "odoo.user_linked",
            {
                "odoo_user_id": row.odoo_user_id,
                "odoo_login": row.odoo_login,
                "odoo_partner_id": row.odoo_partner_id,
                "default_company_id": row.default_company_id,
                "allowed_company_ids": row.allowed_company_ids,
            },
        )
        return _mapping_to_response(row)

    async def unlink_user(self) -> None:
        from app.core.exceptions import JAIOSException

        result = await self.db.execute(
            select(OdooUserMapping).where(
                OdooUserMapping.tenant_id == self.tenant_id,
                OdooUserMapping.jaios_user_id == self.user_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row or not row.is_active:
            raise JAIOSException("No hay usuario Odoo vinculado", code="ODOO_USER_NOT_LINKED")

        row.is_active = False
        row.last_verified_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self._audit(
            "odoo.user_unlinked",
            {
                "odoo_user_id": row.odoo_user_id,
                "odoo_login": row.odoo_login,
            },
        )

    async def get_me(self, *, jaios_email: str, jaios_name: str) -> OdooMeResponse:
        client = await self._client()
        connected = client.is_configured
        company_ctx = await self.get_context_response()
        mapping = await self._get_user_mapping()
        return OdooMeResponse(
            jaios_user_id=self.user_id,
            jaios_email=jaios_email,
            jaios_name=jaios_name,
            odoo_connected=connected,
            company_context=company_ctx,
            user_mapping=_mapping_to_response(mapping) if mapping else None,
            read_only=True,
        )

    async def list_mappings(self) -> list[OdooUserMappingResponse]:
        result = await self.db.execute(
            select(OdooUserMapping).where(OdooUserMapping.tenant_id == self.tenant_id)
        )
        rows = result.scalars().all()
        return [_mapping_to_response(r) for r in rows]


def _mapping_to_response(row: OdooUserMapping) -> OdooUserMappingResponse:
    return OdooUserMappingResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        jaios_user_id=row.jaios_user_id,
        odoo_user_id=row.odoo_user_id,
        odoo_login=row.odoo_login,
        odoo_partner_id=row.odoo_partner_id,
        allowed_company_ids=row.allowed_company_ids or [],
        default_company_id=row.default_company_id,
        is_active=row.is_active,
        last_verified_at=row.last_verified_at,
    )
