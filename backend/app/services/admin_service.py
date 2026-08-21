"""Admin Center — usuarios, módulos, departamentos, reglas, configuración."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.admin_permissions import (
    DEFAULT_DEPARTMENTS,
    DEFAULT_MODULES,
    DEFAULT_ROUTING_RULES,
    VALID_ROLES,
    actor_can_assign_roles,
    can_mutate_admin,
    can_view_admin,
    normalize_role,
    normalize_roles,
    permissions_for_roles,
    primary_role,
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
    AdminResetPasswordRequest,
    AdminResetPasswordResponse,
    AdminUserCreateRequest,
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserRolesRequest,
    AdminUserRolesResponse,
    AdminUserStatusRequest,
    AdminUserStatusResponse,
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
from app.models.task import Task
from app.models.refresh_token import RefreshToken
from datetime import UTC, datetime
from sqlalchemy import and_, or_
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
        membership = await self._actor_membership(user.id)
        roles = self._membership_roles(membership)
        role = primary_role(roles) if membership else normalize_role(get_current_role())
        if not membership:
            roles = normalize_roles([role])
        return AdminAccessResponse(
            can_view=can_view_admin(role, user.is_superadmin, roles=roles),
            can_mutate=can_mutate_admin(role, user.is_superadmin, roles=roles),
            role=role,
            permissions=sorted(permissions_for_roles(roles, is_superadmin=user.is_superadmin)),
        )

    def _membership_roles(self, membership: TenantMembership | None) -> list[str]:
        if not membership:
            return ["usuario"]
        return normalize_roles(
            list(getattr(membership, "roles", None) or []),
            fallback=membership.role,
        )

    async def _actor_membership(self, user_id: uuid.UUID | None) -> TenantMembership | None:
        if not user_id:
            return None
        result = await self.db.execute(
            select(TenantMembership).where(
                TenantMembership.tenant_id == self.tenant_id,
                TenantMembership.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _open_tasks_count(self, user_id: uuid.UUID) -> int:
        closed = ("completada", "completado", "completed", "cancelada", "cancelled", "done")
        result = await self.db.execute(
            select(func.count())
            .select_from(Task)
            .where(
                Task.tenant_id == self.tenant_id,
                Task.assigned_to_id == user_id,
                ~Task.status.in_(closed),
            )
        )
        return int(result.scalar_one() or 0)

    async def _count_owners(self) -> int:
        result = await self.db.execute(
            select(TenantMembership).where(TenantMembership.tenant_id == self.tenant_id)
        )
        return sum(1 for m in result.scalars().all() if "owner" in self._membership_roles(m))

    async def _apply_roles(
        self,
        membership: TenantMembership,
        requested: list[str],
        *,
        actor: User | None,
    ) -> list[str]:
        roles = [r for r in normalize_roles(requested) if r in VALID_ROLES and r != "member"]
        if not roles:
            raise ValueError("Debe asignar al menos un rol válido")

        actor_roles = self._membership_roles(await self._actor_membership(self.actor_id))
        ok, err = actor_can_assign_roles(
            actor_roles=actor_roles,
            actor_is_superadmin=bool(actor and actor.is_superadmin),
            requested_roles=roles,
        )
        if not ok:
            raise ValueError(err or "No autorizado a asignar esos roles")

        previous = self._membership_roles(membership)
        if "owner" in previous and "owner" not in roles and await self._count_owners() <= 1:
            raise ValueError("No se puede quitar el último propietario del tenant")

        membership.roles = roles
        membership.role = primary_role(roles)
        return roles

    async def _bump_credentials(self, user: User) -> None:
        user.credentials_version = int(getattr(user, "credentials_version", 0) or 0) + 1
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        now = datetime.now(UTC)
        for tok in result.scalars().all():
            tok.revoked_at = now

    async def _audit(self, action: str, details: dict | None = None, resource_id: uuid.UUID | None = None) -> None:
        safe = {
            k: v
            for k, v in (details or {}).items()
            if k not in {"password", "password_hash", "confirm_password"}
        }
        await self.audit.log(
            action=action,
            tenant_id=self.tenant_id,
            user_id=self.actor_id,
            resource_type="admin",
            resource_id=resource_id,
            details=safe,
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
        open_tasks_count: int = 0,
    ) -> AdminUserResponse:
        roles = self._membership_roles(membership)
        return AdminUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            role=primary_role(roles),
            roles=roles,
            department=membership.department,
            supervisor_id=membership.supervisor_id,
            supervisor_name=supervisor_name,
            visible_company_ids=membership.visible_company_ids or [],
            odoo_user_id=membership.odoo_user_id,
            m365_prepared=m365 is not None,
            m365_connection_status=m365.connection_status if m365 else None,
            open_tasks_count=open_tasks_count,
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

        items: list[AdminUserResponse] = []
        for u, m in rows:
            items.append(
                self._user_response(
                    u,
                    m,
                    supervisor_name=names.get(m.supervisor_id) if m.supervisor_id else None,
                    m365=m365_map.get(u.id),
                    open_tasks_count=await self._open_tasks_count(u.id),
                )
            )
        return AdminUserListResponse(items=items, total=len(items))

    async def create_user(self, payload: AdminUserCreateRequest) -> AdminUserResponse:
        actor = await self.db.get(User, self.actor_id) if self.actor_id else None
        requested = payload.roles or ([payload.role] if payload.role else ["usuario"])

        existing = await self.db.execute(select(User).where(User.email == payload.email))
        if existing.scalar_one_or_none():
            raise ValueError("El correo ya está registrado")

        user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            is_active=payload.is_active if payload.is_active is not None else True,
        )
        self.db.add(user)
        await self.db.flush()

        membership = TenantMembership(
            tenant_id=self.tenant_id,
            user_id=user.id,
            role="usuario",
            roles=["usuario"],
            department=payload.department,
            supervisor_id=payload.supervisor_id,
            visible_company_ids=payload.visible_company_ids,
            odoo_user_id=payload.odoo_user_id,
        )
        self.db.add(membership)
        await self.db.flush()
        roles = await self._apply_roles(membership, list(requested), actor=actor)
        await self._audit(
            "admin.user_created",
            {"email": user.email, "role": primary_role(roles), "roles": roles},
            user.id,
        )
        await self.db.flush()
        users = await self.list_users()
        item = next((u for u in users.items if u.id == user.id), None)
        if not item:
            raise RuntimeError("Usuario creado pero no encontrado en listado")
        return item

    async def update_user(self, user_id: uuid.UUID, payload: AdminUserUpdateRequest) -> AdminUserResponse | None:
        actor = await self.db.get(User, self.actor_id) if self.actor_id else None
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
            await self._bump_credentials(user)
            await self._audit("admin.password_reset", {"user_id": str(user_id)}, user_id)
        if payload.is_active is not None and payload.is_active != user.is_active:
            await self.set_user_status(user_id, AdminUserStatusRequest(is_active=payload.is_active))
            # reload after status change
            result = await self.db.execute(
                select(User, TenantMembership)
                .join(TenantMembership, TenantMembership.user_id == User.id)
                .where(TenantMembership.tenant_id == self.tenant_id, User.id == user_id)
            )
            row = result.first()
            if not row:
                return None
            user, membership = row
        if payload.roles is not None or payload.role is not None:
            old_roles = self._membership_roles(membership)
            requested = payload.roles if payload.roles is not None else [payload.role or membership.role]
            new_roles = await self._apply_roles(membership, list(requested), actor=actor)
            await self._audit(
                "admin.role_changed",
                {"user_id": str(user_id), "from": old_roles, "to": new_roles},
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
        resp = await self.set_user_status(user_id, AdminUserStatusRequest(is_active=False))
        return resp is not None

    async def set_user_status(
        self, user_id: uuid.UUID, payload: AdminUserStatusRequest
    ) -> AdminUserStatusResponse | None:
        result = await self.db.execute(
            select(User, TenantMembership)
            .join(TenantMembership, TenantMembership.user_id == User.id)
            .where(TenantMembership.tenant_id == self.tenant_id, User.id == user_id)
        )
        row = result.first()
        if not row:
            return None
        user, membership = row
        open_tasks = await self._open_tasks_count(user_id)

        if not payload.is_active:
            if "owner" in self._membership_roles(membership) and await self._count_owners() <= 1:
                raise ValueError("No se puede desactivar el último propietario del tenant")
            if self.actor_id and user_id == self.actor_id:
                raise ValueError("No puede desactivarse a sí mismo")

        user.is_active = payload.is_active
        if not payload.is_active:
            await self._bump_credentials(user)
            await self._audit(
                "admin.user_disabled",
                {"user_id": str(user_id), "open_tasks_count": open_tasks},
                user_id,
            )
            msg = "Usuario desactivado correctamente."
        else:
            await self._audit("admin.user_enabled", {"user_id": str(user_id)}, user_id)
            msg = "Usuario activado correctamente."

        await self.db.flush()
        return AdminUserStatusResponse(
            id=user_id,
            is_active=user.is_active,
            open_tasks_count=open_tasks,
            message=msg,
        )

    async def reset_password(
        self, user_id: uuid.UUID, payload: AdminResetPasswordRequest
    ) -> AdminResetPasswordResponse | None:
        if payload.password != payload.confirm_password:
            raise ValueError("La confirmación de contraseña no coincide")
        if len(payload.password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")

        result = await self.db.execute(
            select(User)
            .join(TenantMembership, TenantMembership.user_id == User.id)
            .where(TenantMembership.tenant_id == self.tenant_id, User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        user.password_hash = hash_password(payload.password)
        await self._bump_credentials(user)
        await self._audit("admin.password_reset", {"user_id": str(user_id)}, user_id)
        await self.db.flush()
        return AdminResetPasswordResponse(id=user_id, message="Contraseña actualizada correctamente.")

    async def set_user_roles(
        self, user_id: uuid.UUID, payload: AdminUserRolesRequest
    ) -> AdminUserRolesResponse | None:
        actor = await self.db.get(User, self.actor_id) if self.actor_id else None
        result = await self.db.execute(
            select(User, TenantMembership)
            .join(TenantMembership, TenantMembership.user_id == User.id)
            .where(TenantMembership.tenant_id == self.tenant_id, User.id == user_id)
        )
        row = result.first()
        if not row:
            return None
        _user, membership = row
        old_roles = self._membership_roles(membership)
        roles = await self._apply_roles(membership, list(payload.roles), actor=actor)
        await self._audit(
            "admin.role_changed",
            {"user_id": str(user_id), "from": old_roles, "to": roles},
            user_id,
        )
        await self.db.flush()
        return AdminUserRolesResponse(
            id=user_id,
            role=primary_role(roles),
            roles=roles,
            message="Roles actualizados.",
        )
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
