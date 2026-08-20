"""Filtrado backend por contexto global multiempresa."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import or_
from sqlalchemy.sql import ColumnElement

from app.core.exceptions import AuthorizationError
from app.services.global_company_context_service import GlobalCompanyContextService

# Odoo res.company name → clave DGCP
DGCP_KEY_BY_NAME: list[tuple[str, str]] = [
    ("just office", "just_office"),
    ("justech", "justech"),
    ("plug", "mf_plug_safe"),
    ("omni", "omni_solutions"),
]


@dataclass
class CompanyScope:
    mode: str
    company_ids: list[int]
    company_names: list[str]
    scope_label: str
    can_select_all: bool

    @property
    def active(self) -> bool:
        return bool(self.company_ids or self.company_names)


class CompanyScopeFilter:
    def __init__(self, db, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._scope: CompanyScope | None = None

    async def scope(self) -> CompanyScope:
        if self._scope is None:
            ctx = await GlobalCompanyContextService(
                self.db, self.tenant_id, self.user_id
            ).get_context()
            self._scope = CompanyScope(
                mode=ctx.selection_mode,
                company_ids=list(ctx.selected_company_ids or []),
                company_names=list(ctx.selected_company_names or []),
                scope_label=ctx.scope_label,
                can_select_all=ctx.can_select_all,
            )
        return self._scope

    @staticmethod
    def odoo_name_to_dgcp_key(name: str) -> str | None:
        lowered = name.lower()
        if "just office" in lowered or "justoffice" in lowered:
            return "just_office"
        if "justech" in lowered:
            return "justech"
        if "plug" in lowered or "plugsafe" in lowered:
            return "mf_plug_safe"
        if "omni" in lowered:
            return "omni_solutions"
        return None

    async def dgcp_company_keys(self) -> list[str]:
        """Claves DGCP del alcance *actualmente seleccionado* (header multiempresa)."""
        sc = await self.scope()
        keys: list[str] = []
        for name in sc.company_names:
            key = self.odoo_name_to_dgcp_key(name)
            if key and key not in keys:
                keys.append(key)
        return keys

    async def allowed_dgcp_company_keys(self) -> list[str]:
        """Claves DGCP de todas las empresas Odoo que el usuario *puede* consultar."""
        allowed = await GlobalCompanyContextService(
            self.db, self.tenant_id, self.user_id
        ).get_allowed()
        keys: list[str] = []
        for item in allowed.items:
            key = self.odoo_name_to_dgcp_key(item.name)
            if key and key not in keys:
                keys.append(key)
        return keys

    async def resolve_odoo_company_id_for_dgcp_key(self, dgcp_key: str) -> int | None:
        """Mapear justech/just_office/... → id de res.company Odoo permitido."""
        allowed = await GlobalCompanyContextService(
            self.db, self.tenant_id, self.user_id
        ).get_allowed()
        needle = (dgcp_key or "").strip().lower()
        for item in allowed.items:
            if self.odoo_name_to_dgcp_key(item.name) == needle:
                return int(item.id)
        return None

    async def task_company_clause(self, company_id_column) -> ColumnElement | None:
        sc = await self.scope()
        if not sc.company_ids:
            return None
        return or_(
            company_id_column.in_(sc.company_ids),
            company_id_column.is_(None),
        )

    async def document_company_clause(self, company_column) -> ColumnElement | None:
        sc = await self.scope()
        if sc.mode == "all" and sc.can_select_all:
            return None
        if not sc.company_names:
            return None
        patterns: list[ColumnElement] = []
        for name in sc.company_names:
            patterns.append(company_column.ilike(f"%{name}%"))
            key = self.odoo_name_to_dgcp_key(name)
            if key:
                patterns.append(company_column.ilike(key))
        return or_(*patterns) if patterns else None

    async def assert_company_name_allowed(self, company_name: str) -> None:
        if not company_name or not company_name.strip():
            return
        sc = await self.scope()
        if not sc.company_names:
            return
        target = company_name.strip().lower()
        for allowed in sc.company_names:
            al = allowed.lower()
            if target in al or al in target:
                return
        key = self.odoo_name_to_dgcp_key(company_name)
        allowed_keys = {self.odoo_name_to_dgcp_key(n) for n in sc.company_names}
        if key and key in allowed_keys:
            return
        raise AuthorizationError(
            f"No tienes visibilidad sobre {company_name.strip()}.",
            code="COMPANY_ACCESS_DENIED",
        )

    async def assert_company_id_allowed(self, company_id: int | None) -> None:
        if company_id is None:
            return
        sc = await self.scope()
        if company_id not in sc.company_ids:
            raise AuthorizationError(
                "No tienes permiso para consultar datos de esa empresa.",
                code="COMPANY_ACCESS_DENIED",
            )

    async def primary_company_id(self) -> int | None:
        sc = await self.scope()
        return sc.company_ids[0] if sc.company_ids else None

    def company_names_match(self, company_filter: str | None) -> list[str] | None:
        """Para search: None = sin filtro explícito (usar scope)."""
        return None if company_filter else None
