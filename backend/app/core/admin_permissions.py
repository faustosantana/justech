"""Roles y permisos — Admin Center."""

from __future__ import annotations

ADMIN_VIEW_ROLES = frozenset({"owner", "admin", "gerencia"})
ADMIN_MUTATE_ROLES = frozenset({"owner", "admin"})

VALID_ROLES = frozenset({
    "owner",
    "admin",
    "gerencia",
    "ventas",
    "facturacion",
    "finanzas",
    "compras",
    "soporte",
    "operaciones",
    "licitaciones",
    "usuario",
    "member",  # legado → tratado como usuario
    "lottery_client",
})


LOTTERY_PERMISSIONS = frozenset({
    "lottery.access",
    "lottery.search",
    "lottery.chat",
    "lottery.compare",
    "lottery.statistics",
    "lottery.export",
    "lottery.share",
    "lottery.saved_queries",
    "lottery.admin",
    "lottery.import",
    "lottery.sync",
    "lottery.audit",
    # Lottery 2.0 aliases / fine-grained
    "lottery_view",
    "lottery_search",
    "lottery_ai",
    "lottery_compare",
    "lottery_export",
    "lottery_admin_lotteries",
    "lottery_admin_sync",
    "lottery_admin_scheduler",
    "lottery_admin_ai",
    "lottery_admin_prompts",
    "lottery_admin_models",
    "lottery_admin_tools",
    "lottery_admin_safety",
})

LOTTERY_CLIENT_PERMISSIONS = frozenset({
    "lottery.access",
    "lottery.search",
    "lottery.chat",
    "lottery.compare",
    "lottery.statistics",
    "lottery.export",
    "lottery.saved_queries",
    "lottery_view",
    "lottery_search",
    "lottery_ai",
    "lottery_compare",
    "lottery_export",
})

PERMISSIONS = frozenset({
    "view_modules",
    "create_tasks",
    "reassign_tasks",
    "view_odoo",
    "view_dgcp",
    # Required by FE MutateButton (hideWhenDenied) + DGCP_MUTATE.
    "mutate_dgcp",
    "view_m365",
    # Restored: FE ModuleAccessGuard for empresas-grupo/documentos requires this key.
    # Dropped accidentally in lottery admin merge (dd19094). Scope: view_documents only.
    "view_documents",
    "admin_users",
    "admin_settings",
}) | LOTTERY_PERMISSIONS

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "owner": PERMISSIONS,
    # lottery perms included via PERMISSIONS for owner/admin
    "admin": PERMISSIONS,
    "gerencia": frozenset({
        "view_modules", "create_tasks", "reassign_tasks",
        "view_odoo", "view_dgcp", "mutate_dgcp", "view_m365", "view_documents",
    }) | LOTTERY_CLIENT_PERMISSIONS,
    "ventas": frozenset({
        "view_modules", "create_tasks", "view_odoo", "view_dgcp", "mutate_dgcp", "view_m365", "view_documents",
    }),
    "facturacion": frozenset({
        "view_modules", "create_tasks", "view_odoo", "view_m365", "view_documents",
    }),
    "finanzas": frozenset({
        "view_modules", "create_tasks", "view_odoo", "view_m365", "view_documents",
    }),
    "compras": frozenset({
        "view_modules", "create_tasks", "view_odoo", "view_documents",
    }),
    "soporte": frozenset({
        "view_modules", "create_tasks", "reassign_tasks", "view_odoo", "view_m365", "view_documents",
    }),
    "operaciones": frozenset({
        "view_modules", "create_tasks", "reassign_tasks",
        "view_odoo", "view_dgcp", "mutate_dgcp", "view_m365", "view_documents",
    }),
    "licitaciones": frozenset({
        "view_modules", "create_tasks", "view_dgcp", "mutate_dgcp", "view_m365", "view_documents",
    }),
    "usuario": frozenset({
        "view_modules", "create_tasks", "view_odoo", "view_dgcp", "mutate_dgcp", "view_m365", "view_documents",
    }),
    "member": frozenset({
        "view_modules", "create_tasks", "view_odoo", "view_dgcp", "mutate_dgcp", "view_m365", "view_documents",
    }),
    # Lottery-only: must not gain empresas-grupo / documentos.
    "lottery_client": LOTTERY_CLIENT_PERMISSIONS,
}

DEFAULT_MODULES = [
    ("dashboard", "Panel Principal", False),
    ("dgcp", "DGCP", False),
    ("odoo", "Odoo", False),
    ("m365", "Microsoft 365", False),
    ("work", "Centro de Trabajo", False),
    ("tasks", "Tareas", False),
    ("notifications", "Notificaciones", False),
    ("enterprise_search", "Búsqueda empresarial", True),
    ("suppliers", "Proveedores", True),
    ("prices", "Precios", True),
    ("documents", "Documentos", True),
    ("hermes", "Hermes", True),
    ("lottery", "Resultados de Loterías", True),
]

DEFAULT_DEPARTMENTS = [
    ("ventas", "Ventas"),
    ("facturacion", "Facturación"),
    ("finanzas", "Finanzas"),
    ("administracion", "Administración"),
    ("soporte", "Soporte"),
    ("operaciones", "Operaciones"),
    ("compras", "Compras"),
    ("gerencia", "Gerencia"),
    ("licitaciones", "Licitaciones"),
]

DEFAULT_ROUTING_RULES = [
    {
        "event_type": "solicitud_cotizacion",
        "name": "Solicitud de cotización",
        "category": "cotizacion",
        "department": "ventas",
        "default_priority": "media",
        "default_assignee_name": "Marieli",
        "default_supervisor_name": "Fausto",
        "due_hours": 24,
        "notification_message": "Nueva solicitud de cotización asignada",
        "checklist_template": [
            "Validar requerimiento del cliente",
            "Preparar cotización",
            "Revisar precios y márgenes",
            "Enviar cotización al cliente",
        ],
    },
    {
        "event_type": "factura_proveedor",
        "name": "Factura de proveedor",
        "category": "factura_proveedor",
        "department": "administracion",
        "default_priority": "alta",
        "default_assignee_name": "Diana",
        "default_supervisor_name": None,
        "due_hours": 24,
        "notification_message": "Nueva factura de proveedor para registrar",
        "checklist_template": [
            "Validar proveedor",
            "Validar RNC",
            "Validar monto",
            "Registrar factura en Odoo",
        ],
    },
    {
        "event_type": "factura_cliente",
        "name": "Factura de cliente",
        "category": "factura_cliente",
        "department": "facturacion",
        "default_priority": "alta",
        "default_assignee_name": "Jennipher",
        "default_supervisor_name": "Fausto",
        "due_hours": 24,
        "notification_message": "Nueva factura de cliente",
        "checklist_template": [],
    },
    {
        "event_type": "soporte_critico",
        "name": "Soporte crítico",
        "category": "soporte",
        "department": "soporte",
        "default_priority": "critica",
        "default_assignee_name": "Felipe Mejía",
        "default_supervisor_name": "Jesús",
        "due_hours": 4,
        "notification_message": "Incidente de soporte crítico",
        "checklist_template": ["Diagnosticar", "Escalar si aplica", "Resolver y documentar"],
    },
    {
        "event_type": "licitacion",
        "name": "Licitación DGCP",
        "category": "licitacion",
        "department": "licitaciones",
        "default_priority": "alta",
        "default_assignee_name": "Fausto",
        "default_supervisor_name": None,
        "due_hours": 48,
        "notification_message": "Nueva oportunidad de licitación",
        "checklist_template": ["Revisar pliego", "Evaluar viabilidad", "Preparar propuesta"],
    },
]


def normalize_role(role: str | None) -> str:
    if not role:
        return "usuario"
    return "usuario" if role == "member" else role


ROLE_PRIORITY: tuple[str, ...] = (
    "owner", "admin", "gerencia", "operaciones", "licitaciones",
    "ventas", "finanzas", "facturacion", "compras", "soporte", "usuario", "lottery_client",
)

_VIEW_TO_MUTATE = {
    "view_dgcp": "mutate_dgcp",
    "view_odoo": "mutate_odoo",
    "view_m365": "mutate_m365",
    "view_documents": "mutate_documents",
}


def normalize_roles(roles: list[str] | tuple[str, ...] | set[str] | None, *, fallback: str | None = None) -> list[str]:
    raw = list(roles or [])
    if not raw and fallback:
        raw = [fallback]
    out: list[str] = []
    seen: set[str] = set()
    for r in raw:
        nr = normalize_role(r)
        if nr == "member":
            nr = "usuario"
        if nr not in VALID_ROLES:
            continue
        if nr in seen:
            continue
        seen.add(nr)
        out.append(nr)
    if not out:
        fb = normalize_role(fallback) if fallback else "usuario"
        out = [fb if fb in VALID_ROLES else "usuario"]
    return out


def primary_role(roles: list[str] | None, *, fallback: str | None = None) -> str:
    normalized = normalize_roles(roles, fallback=fallback)
    priority = {r: i for i, r in enumerate(ROLE_PRIORITY)}
    return sorted(normalized, key=lambda r: priority.get(r, 999))[0]


def permissions_for_roles(roles: list[str] | None, *, is_superadmin: bool = False) -> frozenset[str]:
    if is_superadmin:
        return PERMISSIONS
    union: set[str] = set()
    for role in normalize_roles(roles):
        union |= set(ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["usuario"]))
    # Compat: roles with view_X also get mutate_X used by DGCP_MUTATE gates.
    for view, mutate in _VIEW_TO_MUTATE.items():
        if view in union and mutate in PERMISSIONS:
            union.add(mutate)
    return frozenset(union)


def roles_have_permission(roles: list[str] | None, permission: str, *, is_superadmin: bool = False) -> bool:
    return permission in permissions_for_roles(roles, is_superadmin=is_superadmin)


def actor_can_assign_roles(
    *,
    actor_roles: list[str],
    actor_is_superadmin: bool,
    requested_roles: list[str],
) -> tuple[bool, str | None]:
    if actor_is_superadmin:
        return True, None
    actor = normalize_roles(actor_roles)
    requested = normalize_roles(requested_roles)
    if "owner" in requested and "owner" not in actor:
        return False, "Solo un propietario puede asignar el rol Propietario"
    if not can_mutate_admin(None, roles=actor):
        return False, "Sin permiso para administrar roles"
    return True, None


def can_view_admin(role: str | None, is_superadmin: bool = False, roles: list[str] | None = None) -> bool:
    if is_superadmin:
        return True
    check = normalize_roles(roles, fallback=role)
    return any(r in ADMIN_VIEW_ROLES for r in check)


def can_mutate_admin(role: str | None, is_superadmin: bool = False, roles: list[str] | None = None) -> bool:
    if is_superadmin:
        return True
    check = normalize_roles(roles, fallback=role)
    return any(r in ADMIN_MUTATE_ROLES for r in check)


def permissions_for_role(role: str | None) -> list[str]:
    return sorted(ROLE_PERMISSIONS.get(normalize_role(role), ROLE_PERMISSIONS["usuario"]))


def role_has_permission(role: str | None, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(normalize_role(role), ROLE_PERMISSIONS["usuario"])
