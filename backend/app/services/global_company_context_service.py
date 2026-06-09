"""Contexto global multiempresa — Justech, Just Office, PlugSafe, Omni."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import JAIOSException
from app.core.tenant import get_current_role
from app.models.odoo_context import OdooUserMapping, UserCompanyContext
from app.models.tenant import TenantMembership
from app.schemas.company_context import (
    AllowedCompaniesResponse,
    CompanyOption,
    GlobalCompanyContextResponse,
    GlobalCompanyContextUpdate,
    UserCompaniesAdminResponse,
    UserCompaniesAdminUpdate,
)
from app.services.odoo_company_service import OdooCompanyContextService
from integrations.odoo.company_context import OdooCompanyContext

ROLES_CAN_SELECT_ALL = frozenset({"owner", "admin", "gerencia"})


class GlobalCompanyContextService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    def _odoo(self):
        from app.services.odoo_service import OdooService

        return OdooService(self.db, self.tenant_id, user_id=self.user_id)

    async def _membership(self) -> TenantMembership | None:
        result = await self.db.execute(
            select(TenantMembership).where(
                TenantMembership.tenant_id == self.tenant_id,
                TenantMembership.user_id == self.user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _context_row(self) -> UserCompanyContext | None:
        result = await self.db.execute(
            select(UserCompanyContext).where(
                UserCompanyContext.tenant_id == self.tenant_id,
                UserCompanyContext.jaios_user_id == self.user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _mapping(self) -> OdooUserMapping | None:
        result = await self.db.execute(
            select(OdooUserMapping).where(
                OdooUserMapping.tenant_id == self.tenant_id,
                OdooUserMapping.jaios_user_id == self.user_id,
                OdooUserMapping.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _allowed_company_map(self) -> tuple[dict[int, str], bool]:
        svc = OdooCompanyContextService(
            self.db,
            self.tenant_id,
            self.user_id,
            odoo_client_factory=self._odoo()._bare_client,
        )
        companies = await svc.list_companies()
        if not companies.connected:
            fallback = await self._fallback_company_map()
            return fallback, False
        membership = await self._membership()
        visible = set(membership.visible_company_ids or []) if membership else set()
        items = companies.items
        if visible:
            items = [c for c in items if c.id in visible]
        return {c.id: c.name for c in items}, True

    async def _fallback_company_map(self) -> dict[int, str]:
        row = await self._context_row()
        if not row or not row.odoo_company_id:
            return {}
        names: dict[int, str] = {}
        if row.odoo_company_name:
            names[row.odoo_company_id] = row.odoo_company_name
        for cid in row.selected_company_ids or []:
            if cid not in names and cid == row.odoo_company_id and row.odoo_company_name:
                names[cid] = row.odoo_company_name
        membership = await self._membership()
        visible = set(membership.visible_company_ids or []) if membership else set()
        if visible:
            names = {k: v for k, v in names.items() if k in visible}
        return names

    def _can_select_all(self, membership: TenantMembership | None) -> bool:
        role = get_current_role() or (membership.role if membership else "usuario")
        if membership and membership.role in ROLES_CAN_SELECT_ALL:
            return True
        return role in ROLES_CAN_SELECT_ALL

    async def get_allowed(self) -> AllowedCompaniesResponse:
        company_map, _ = await self._allowed_company_map()
        mapping = await self._mapping()
        row = await self._context_row()
        selected = set(row.selected_company_ids or []) if row else set()
        if row and row.selection_mode == "single" and row.odoo_company_id:
            selected = {row.odoo_company_id}
        membership = await self._membership()
        return AllowedCompaniesResponse(
            items=[
                CompanyOption(id=cid, name=name, selected=cid in selected)
                for cid, name in sorted(company_map.items(), key=lambda x: x[1].lower())
            ],
            can_select_all=self._can_select_all(membership),
            default_company_id=mapping.default_company_id if mapping else None,
            updated_at=row.selected_at if row else None,
        )

    async def get_context(self) -> GlobalCompanyContextResponse:
        company_map, odoo_connected = await self._allowed_company_map()
        membership = await self._membership()
        row = await self._context_row()
        can_all = self._can_select_all(membership)

        if not company_map:
            return GlobalCompanyContextResponse(
                scope_label="Sin empresas disponibles",
                odoo_connected=odoo_connected,
                can_select_all=can_all,
            )

        mode = row.selection_mode if row else "single"
        selected_ids: list[int] = list(row.selected_company_ids or []) if row else []
        active_id = row.odoo_company_id if row else None
        active_name = row.odoo_company_name if row else None

        if row and mode == "single" and active_id:
            selected_ids = [active_id]
        elif row and mode == "all" and can_all:
            selected_ids = list(company_map.keys())
        elif row and mode == "multi":
            selected_ids = [cid for cid in selected_ids if cid in company_map]
            if selected_ids and not active_id:
                active_id = selected_ids[0]
                active_name = company_map.get(active_id)

        selected_names = [company_map[cid] for cid in selected_ids if cid in company_map]
        scope = self._scope_label(mode, selected_names, can_all)

        return GlobalCompanyContextResponse(
            selection_mode=mode,
            active_company_id=active_id,
            active_company_name=active_name,
            selected_company_ids=selected_ids,
            selected_company_names=selected_names,
            allowed_companies=[
                CompanyOption(id=cid, name=name, selected=cid in set(selected_ids))
                for cid, name in sorted(company_map.items(), key=lambda x: x[1].lower())
            ],
            can_select_all=can_all,
            can_select_multiple=True,
            scope_label=scope,
            odoo_connected=odoo_connected,
        )

    @staticmethod
    def _scope_label(mode: str, names: list[str], can_all: bool) -> str:
        if mode == "all" and can_all:
            return "Consultando en: Todas las empresas"
        if len(names) == 1:
            return f"Consultando en: {names[0]}"
        if len(names) > 1:
            shown = ", ".join(names[:3])
            suffix = f" (+{len(names) - 3})" if len(names) > 3 else ""
            return f"Consultando en: {shown}{suffix}"
        return "Sin empresa seleccionada"

    async def set_context(self, payload: GlobalCompanyContextUpdate) -> GlobalCompanyContextResponse:
        company_map, _ = await self._allowed_company_map()
        if not company_map:
            raise JAIOSException("No hay empresas Odoo disponibles", code="NO_COMPANIES")

        membership = await self._membership()
        can_all = self._can_select_all(membership)
        mode = payload.selection_mode

        if mode == "all":
            if not can_all:
                raise JAIOSException(
                    "No tienes permiso para consultar todas las empresas",
                    code="COMPANY_ALL_DENIED",
                )
            selected_ids = list(company_map.keys())
            active_id = selected_ids[0]
        elif mode == "multi":
            selected_ids = [cid for cid in payload.selected_company_ids if cid in company_map]
            if not selected_ids:
                raise JAIOSException("Selecciona al menos una empresa", code="COMPANY_REQUIRED")
            active_id = payload.active_company_id or selected_ids[0]
            if active_id not in selected_ids:
                active_id = selected_ids[0]
        else:
            active_id = payload.active_company_id or payload.selected_company_ids[0] if payload.selected_company_ids else None
            if active_id is None:
                raise JAIOSException("Empresa activa requerida", code="COMPANY_REQUIRED")
            if active_id not in company_map:
                raise JAIOSException("Empresa no permitida", code="COMPANY_NOT_ALLOWED")
            selected_ids = [active_id]
            mode = "single"

        if active_id not in company_map:
            active_id = selected_ids[0]

        row = await self._context_row()
        now = datetime.now(timezone.utc)
        active_name = company_map[active_id]
        if row:
            row.odoo_company_id = active_id
            row.odoo_company_name = active_name
            row.selection_mode = mode
            row.selected_company_ids = selected_ids
            row.selected_at = now
        else:
            row = UserCompanyContext(
                tenant_id=self.tenant_id,
                jaios_user_id=self.user_id,
                odoo_company_id=active_id,
                odoo_company_name=active_name,
                selection_mode=mode,
                selected_company_ids=selected_ids,
                selected_at=now,
            )
            self.db.add(row)
        await self.db.commit()
        return await self.get_context()

    async def resolve_odoo_context(self) -> OdooCompanyContext | None:
        row = await self._context_row()
        if not row or not row.odoo_company_id:
            return None
        membership = await self._membership()
        mode = row.selection_mode or "single"
        selected_ids = list(row.selected_company_ids or [])
        if mode == "single":
            selected_ids = [row.odoo_company_id]
        elif mode == "all":
            if not self._can_select_all(membership):
                selected_ids = [row.odoo_company_id]
            elif not selected_ids:
                selected_ids = [row.odoo_company_id]
        elif mode == "multi" and not selected_ids:
            selected_ids = [row.odoo_company_id]
        if not selected_ids:
            return None
        primary = row.odoo_company_id or selected_ids[0]
        return OdooCompanyContext(company_id=primary, allowed_company_ids=tuple(selected_ids))

    async def get_active_company_names(self) -> list[str]:
        ctx = await self.get_context()
        return ctx.selected_company_names

    async def admin_get_user_companies(self, target_user_id: uuid.UUID) -> UserCompaniesAdminResponse:
        from app.models.tenant import TenantMembership
        from app.models.odoo_context import OdooUserMapping

        result = await self.db.execute(
            select(TenantMembership).where(
                TenantMembership.tenant_id == self.tenant_id,
                TenantMembership.user_id == target_user_id,
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise JAIOSException("Usuario no encontrado", code="USER_NOT_FOUND")

        map_result = await self.db.execute(
            select(OdooUserMapping).where(
                OdooUserMapping.tenant_id == self.tenant_id,
                OdooUserMapping.jaios_user_id == target_user_id,
                OdooUserMapping.is_active.is_(True),
            )
        )
        mapping = map_result.scalar_one_or_none()

        svc = OdooCompanyContextService(
            self.db,
            self.tenant_id,
            target_user_id,
            odoo_client_factory=self._odoo()._bare_client,
        )
        companies = await svc.list_companies()
        company_map = {c.id: c.name for c in companies.items} if companies.connected else {}
        visible = list(membership.visible_company_ids or []) if membership.visible_company_ids else list(company_map.keys())
        names = [company_map[cid] for cid in visible if cid in company_map]
        default_id = membership.default_company_id
        if default_id is None and mapping:
            default_id = mapping.default_company_id
        return UserCompaniesAdminResponse(
            user_id=target_user_id,
            visible_company_ids=visible,
            visible_company_names=names,
            available_companies=[
                CompanyOption(id=cid, name=name, selected=cid in set(visible))
                for cid, name in sorted(company_map.items(), key=lambda x: x[1].lower())
            ],
            default_company_id=default_id,
            can_select_all=membership.role in ROLES_CAN_SELECT_ALL,
            user_role=membership.role,
            odoo_allowed_company_ids=mapping.allowed_company_ids if mapping else [],
        )

    async def admin_set_user_companies(
        self, target_user_id: uuid.UUID, payload: UserCompaniesAdminUpdate
    ) -> UserCompaniesAdminResponse:
        result = await self.db.execute(
            select(TenantMembership).where(
                TenantMembership.tenant_id == self.tenant_id,
                TenantMembership.user_id == target_user_id,
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise JAIOSException("Usuario no encontrado", code="USER_NOT_FOUND")
        membership.visible_company_ids = payload.visible_company_ids
        if payload.can_select_all is not None and membership.role not in ROLES_CAN_SELECT_ALL:
            if payload.can_select_all:
                raise JAIOSException(
                    "Solo roles owner/admin/gerencia pueden ver todas las empresas",
                    code="COMPANY_ALL_DENIED",
                )
        if payload.default_company_id is not None:
            membership.default_company_id = payload.default_company_id
            mapping = await self.db.execute(
                select(OdooUserMapping).where(
                    OdooUserMapping.tenant_id == self.tenant_id,
                    OdooUserMapping.jaios_user_id == target_user_id,
                    OdooUserMapping.is_active.is_(True),
                )
            )
            odoo_map = mapping.scalar_one_or_none()
            if odoo_map:
                odoo_map.default_company_id = payload.default_company_id
        await self.db.commit()
        return await self.admin_get_user_companies(target_user_id)
