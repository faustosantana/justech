"""Admin Center — usuarios, módulos, departamentos, reglas, configuración."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.admin_permissions import (
    DEFAULT_DEPARTMENTS,
    DEFAULT_MODULES,
    DEFAULT_ROUTING_RULES,
    VALID_ROLES,
    can_mutate_admin,
    can_view_admin,
    normalize_role,
    permissions_for_role,
)
from app.core.security import hash_password
from app.core.tenant import get_current_role
from app.models.department import Department
from app.models.m365_account import M365UserAccount
from app.models.routing_rule import RoutingRule
from app.models.tenant import Tenant, TenantMembership
from app.models.tenant_module import TenantModule
from app.models.user import User
from app.schemas.admin import (
    AdminAccessResponse,
    AdminUserCreateRequest,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdateRequest,
    DepartmentCreateRequest,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdateRequest,
    RoleInfoResponse,
    RoleListResponse,
    RoutingRuleAdminResponse,
    RoutingRuleListResponse,
    RoutingRuleUpdateRequest,
    TenantModuleListResponse,
    TenantModuleResponse,
    TenantSettingsResponse,
)
from app.services.audit_service import AuditService
from app.services.routing_service import RoutingService

ROLE_LABELS = {
    "owner": "Propietario",
    "admin": "Administrador",
    "gerencia": "Gerencia",
    "ventas": "Ventas",
    "facturacion": "Facturación",
    "finanzas": "Finanzas",
    "compras": "Compras",
    "soporte": "Soporte",
    "operaciones": "Operaciones",
    "licitaciones": "Licitaciones",
    "usuario": "Usuario",
    "member": "Usuario",
}


class AdminService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, actor_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.actor_id = actor_id
        self.audit = AuditService(db)
        self.routing = RoutingService(db, tenant_id)

    async def access_info(self, user: User) -> AdminAccessResponse:
        role = normalize_role(get_current_role())
        return AdminAccessResponse(
            can_view=can_view_admin(role, user.is_superadmin),
            can_mutate=can_mutate_admin(role, user.is_superadmin),
            role=role,
            permissions=permissions_for_role(role),
        )

    async def _audit(self, action: str, details: dict | None = None, resource_id: uuid.UUID | None = None) -> None:
        await self.audit.log(
            action=action,
            tenant_id=self.tenant_id,
            user_id=self.actor_id,
            resource_type="admin",
            resource_id=resource_id,
            details=details or {},
        )

    async def ensure_defaults(self) -> None:
        mod_count = await self.db.execute(
            select(func.count()).select_from(TenantModule).where(TenantModule.tenant_id == self.tenant_id)
        )
        if mod_count.scalar_one() == 0:
            for key, name, is_future in DEFAULT_MODULES:
                self.db.add(
                    TenantModule(
                        tenant_id=self.tenant_id,
                        module_key=key,
                        name=name,
                        is_enabled=not is_future,
                        is_future=is_future,
                    )
                )

        dept_count = await self.db.execute(
            select(func.count()).select_from(Department).where(Department.tenant_id == self.tenant_id)
        )
        if dept_count.scalar_one() == 0:
            for key, name in DEFAULT_DEPARTMENTS:
                self.db.add(Department(tenant_id=self.tenant_id, key=key, name=name, is_active=True))

        rule_count = await self.db.execute(
            select(func.count()).select_from(RoutingRule).where(RoutingRule.tenant_id == self.tenant_id)
        )
        if rule_count.scalar_one() == 0:
            for rule in DEFAULT_ROUTING_RULES:
                assignee_id = await self.routing.resolve_assignee_id(rule.get("default_assignee_name"))
                supervisor_id = await self.routing.resolve_assignee_id(rule.get("default_supervisor_name"))
                self.db.add(
                    RoutingRule(
                        tenant_id=self.tenant_id,
                        event_type=rule["event_type"],
                        name=rule["name"],
                        category=rule["category"],
                        department=rule["department"],
                        default_priority=rule["default_priority"],
                        default_assignee_name=rule.get("default_assignee_name"),
                        default_assignee_id=assignee_id,
                        default_supervisor_name=rule.get("default_supervisor_name"),
                        default_supervisor_id=supervisor_id,
                        due_hours=rule.get("due_hours"),
                        notification_message=rule.get("notification_message"),
                        checklist_template=rule.get("checklist_template", []),
                        is_active=True,
                    )
                )
        await self.db.flush()

    def _user_response(
        self,
        user: User,
        membership: TenantMembership,
        *,
        supervisor_name: str | None = None,
        m365: M365UserAccount | None = None,
    ) -> AdminUserResponse:
        return AdminUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            role=normalize_role(membership.role),
            department=membership.department,
            supervisor_id=membership.supervisor_id,
            supervisor_name=supervisor_name,
            visible_company_ids=membership.visible_company_ids or [],
            odoo_user_id=membership.odoo_user_id,
            m365_prepared=m365 is not None,
            m365_connection_status=m365.connection_status if m365 else None,
            created_at=user.created_at,
        )

    async def list_users(self) -> AdminUserListResponse:
        await self.ensure_defaults()
        result = await self.db.execute(
            select(User, TenantMembership)
            .join(TenantMembership, TenantMembership.user_id == User.id)
            .where(TenantMembership.tenant_id == self.tenant_id)
            .order_by(User.full_name.asc())
        )
        rows = result.all()
        supervisor_ids = {m.supervisor_id for _, m in rows if m.supervisor_id}
        names: dict[uuid.UUID, str] = {}
        if supervisor_ids:
            sr = await self.db.execute(select(User.id, User.full_name).where(User.id.in_(supervisor_ids)))
            names = {r[0]: r[1] for r in sr.all()}

        m365_map: dict[uuid.UUID, M365UserAccount] = {}
        mr = await self.db.execute(
            select(M365UserAccount).where(M365UserAccount.tenant_id == self.tenant_id)
        )
        for acc in mr.scalars().all():
            m365_map[acc.jaios_user_id] = acc

        items = [
            self._user_response(
                u, m,
                supervisor_name=names.get(m.supervisor_id) if m.supervisor_id else None,
                m365=m365_map.get(u.id),
            )
            for u, m in rows
        ]
        return AdminUserListResponse(items=items, total=len(items))

    async def create_user(self, payload: AdminUserCreateRequest) -> AdminUserResponse:
        role = normalize_role(payload.role)
        if role not in VALID_ROLES:
            raise ValueError(f"Rol inválido: {payload.role}")

        existing = await self.db.execute(select(User).where(User.email == payload.email))
        if existing.scalar_one_or_none():
            raise ValueError("El correo ya está registrado")

        user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()

        membership = TenantMembership(
            tenant_id=self.tenant_id,
            user_id=user.id,
            role=role,
            department=payload.department,
            supervisor_id=payload.supervisor_id,
            visible_company_ids=payload.visible_company_ids,
            odoo_user_id=payload.odoo_user_id,
        )
        self.db.add(membership)
        await self._audit("admin.user_created", {"email": user.email, "role": role}, user.id)
        await self.db.flush()
        users = await self.list_users()
        item = next((u for u in users.items if u.id == user.id), None)
        if not item:
            raise RuntimeError("Usuario creado pero no encontrado en listado")
        return item

    async def update_user(self, user_id: uuid.UUID, payload: AdminUserUpdateRequest) -> AdminUserResponse | None:
        result = await self.db.execute(
            select(User, TenantMembership)
            .join(TenantMembership, TenantMembership.user_id == User.id)
            .where(TenantMembership.tenant_id == self.tenant_id, User.id == user_id)
        )
        row = result.first()
        if not row:
            return None
        user, membership = row

        if payload.email is not None:
            user.email = payload.email
        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.password:
            user.password_hash = hash_password(payload.password)
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.role is not None:
            old_role = membership.role
            membership.role = normalize_role(payload.role)
            await self._audit(
                "admin.role_changed",
                {"user_id": str(user_id), "from": old_role, "to": membership.role},
                user_id,
            )
        if payload.department is not None:
            membership.department = payload.department
        if payload.supervisor_id is not None:
            membership.supervisor_id = payload.supervisor_id
        if payload.visible_company_ids is not None:
            membership.visible_company_ids = payload.visible_company_ids
        if payload.odoo_user_id is not None:
            membership.odoo_user_id = payload.odoo_user_id

        await self._audit("admin.user_updated", {"user_id": str(user_id)}, user_id)
        await self.db.flush()
        users = await self.list_users()
        return next((u for u in users.items if u.id == user_id), None)

    async def disable_user(self, user_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            select(User)
            .join(TenantMembership, TenantMembership.user_id == User.id)
            .where(TenantMembership.tenant_id == self.tenant_id, User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return False
        user.is_active = False
        await self._audit("admin.user_disabled", {"user_id": str(user_id)}, user_id)
        await self.db.flush()
        return True

    async def list_roles(self) -> RoleListResponse:
        items = [
            RoleInfoResponse(
                key=normalize_role(k),
                label=ROLE_LABELS.get(k, k),
                permissions=sorted(permissions_for_role(k)),
            )
            for k in sorted(VALID_ROLES - {"member"})
        ]
        return RoleListResponse(items=items)

    async def list_modules(self) -> TenantModuleListResponse:
        await self.ensure_defaults()
        result = await self.db.execute(
            select(TenantModule)
            .where(TenantModule.tenant_id == self.tenant_id)
            .order_by(TenantModule.is_future.asc(), TenantModule.name.asc())
        )
        items = [
            TenantModuleResponse(
                module_key=m.module_key,
                name=m.name,
                is_enabled=m.is_enabled,
                is_future=m.is_future,
            )
            for m in result.scalars().all()
        ]
        return TenantModuleListResponse(items=items)

    async def update_module(self, module_key: str, is_enabled: bool) -> TenantModuleResponse | None:
        result = await self.db.execute(
            select(TenantModule).where(
                TenantModule.tenant_id == self.tenant_id,
                TenantModule.module_key == module_key,
            )
        )
        mod = result.scalar_one_or_none()
        if not mod:
            return None
        mod.is_enabled = is_enabled
        await self._audit("admin.module_toggled", {"module_key": module_key, "is_enabled": is_enabled})
        await self.db.flush()
        return TenantModuleResponse(
            module_key=mod.module_key,
            name=mod.name,
            is_enabled=mod.is_enabled,
            is_future=mod.is_future,
        )

    async def list_departments(self) -> DepartmentListResponse:
        await self.ensure_defaults()
        result = await self.db.execute(
            select(Department)
            .where(Department.tenant_id == self.tenant_id)
            .order_by(Department.name.asc())
        )
        items = [
            DepartmentResponse(id=d.id, key=d.key, name=d.name, is_active=d.is_active)
            for d in result.scalars().all()
        ]
        return DepartmentListResponse(items=items)

    async def create_department(self, payload: DepartmentCreateRequest) -> DepartmentResponse:
        dept = Department(
            tenant_id=self.tenant_id,
            key=payload.key,
            name=payload.name,
            is_active=True,
        )
        self.db.add(dept)
        await self.db.flush()
        return DepartmentResponse(id=dept.id, key=dept.key, name=dept.name, is_active=dept.is_active)

    async def update_department(
        self, dept_id: uuid.UUID, payload: DepartmentUpdateRequest
    ) -> DepartmentResponse | None:
        result = await self.db.execute(
            select(Department).where(Department.id == dept_id, Department.tenant_id == self.tenant_id)
        )
        dept = result.scalar_one_or_none()
        if not dept:
            return None
        if payload.name is not None:
            dept.name = payload.name
        if payload.is_active is not None:
            dept.is_active = payload.is_active
        await self.db.flush()
        return DepartmentResponse(id=dept.id, key=dept.key, name=dept.name, is_active=dept.is_active)

    async def list_routing_rules(self) -> RoutingRuleListResponse:
        await self.ensure_defaults()
        result = await self.db.execute(
            select(RoutingRule)
            .where(RoutingRule.tenant_id == self.tenant_id)
            .order_by(RoutingRule.name.asc())
        )
        items = [self._rule_response(r) for r in result.scalars().all()]
        return RoutingRuleListResponse(items=items)

    def _rule_response(self, r: RoutingRule) -> RoutingRuleAdminResponse:
        return RoutingRuleAdminResponse(
            id=r.id,
            event_type=r.event_type,
            name=r.name,
            category=r.category,
            department=r.department,
            default_priority=r.default_priority,
            default_assignee_name=r.default_assignee_name,
            default_assignee_id=r.default_assignee_id,
            default_supervisor_name=r.default_supervisor_name,
            default_supervisor_id=r.default_supervisor_id,
            due_hours=r.due_hours,
            notification_message=r.notification_message,
            checklist_template=r.checklist_template or [],
            is_active=r.is_active,
        )

    async def update_routing_rule(
        self, rule_id: uuid.UUID, payload: RoutingRuleUpdateRequest
    ) -> RoutingRuleAdminResponse | None:
        result = await self.db.execute(
            select(RoutingRule).where(RoutingRule.id == rule_id, RoutingRule.tenant_id == self.tenant_id)
        )
        rule = result.scalar_one_or_none()
        if not rule:
            return None
        updates = payload.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(rule, key, value)
        if payload.default_assignee_name and not payload.default_assignee_id:
            rule.default_assignee_id = await self.routing.resolve_assignee_id(payload.default_assignee_name)
        if payload.default_supervisor_name and not payload.default_supervisor_id:
            rule.default_supervisor_id = await self.routing.resolve_assignee_id(payload.default_supervisor_name)
        await self._audit("admin.routing_rule_updated", {"rule_id": str(rule_id), **updates}, rule_id)
        await self.db.flush()
        return self._rule_response(rule)

    async def get_settings(self) -> TenantSettingsResponse:
        result = await self.db.execute(select(Tenant).where(Tenant.id == self.tenant_id))
        tenant = result.scalar_one()
        settings = tenant.settings or {}
        return TenantSettingsResponse(
            language=settings.get("language", "es-DO"),
            timezone=settings.get("timezone", "America/Santo_Domingo"),
            default_currency=settings.get("default_currency", "DOP"),
            primary_company=settings.get("primary_company"),
            qa_policies_visible=settings.get("qa_policies_visible", True),
            integration_status=settings.get("integration_status", {
                "odoo": "activo",
                "dgcp": "activo",
                "m365": "preparación",
                "n8n": "activo",
            }),
        )
