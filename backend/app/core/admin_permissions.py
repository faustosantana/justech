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
    "view_m365",
    "admin_users",
    "admin_settings",
}) | LOTTERY_PERMISSIONS

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "owner": PERMISSIONS,
    # lottery perms included via PERMISSIONS for owner/admin
    "admin": PERMISSIONS,
    "gerencia": frozenset({
        "view_modules", "create_tasks", "reassign_tasks",
        "view_odoo", "view_dgcp", "view_m365",
    }) | LOTTERY_CLIENT_PERMISSIONS,
    "ventas": frozenset({"view_modules", "create_tasks", "view_odoo", "view_dgcp", "view_m365"}),
    "facturacion": frozenset({"view_modules", "create_tasks", "view_odoo", "view_m365"}),
    "finanzas": frozenset({"view_modules", "create_tasks", "view_odoo", "view_m365"}),
    "compras": frozenset({"view_modules", "create_tasks", "view_odoo"}),
    "soporte": frozenset({"view_modules", "create_tasks", "reassign_tasks", "view_odoo", "view_m365"}),
    "operaciones": frozenset({"view_modules", "create_tasks", "reassign_tasks", "view_odoo", "view_dgcp", "view_m365"}),
    "licitaciones": frozenset({"view_modules", "create_tasks", "view_dgcp", "view_m365"}),
    "usuario": frozenset({"view_modules", "create_tasks", "view_odoo", "view_dgcp", "view_m365"}),
    "member": frozenset({"view_modules", "create_tasks", "view_odoo", "view_dgcp", "view_m365"}),
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


def can_view_admin(role: str | None, is_superadmin: bool = False) -> bool:
    if is_superadmin:
        return True
    return normalize_role(role) in ADMIN_VIEW_ROLES


def can_mutate_admin(role: str | None, is_superadmin: bool = False) -> bool:
    if is_superadmin:
        return True
    return normalize_role(role) in ADMIN_MUTATE_ROLES


def permissions_for_role(role: str | None) -> list[str]:
    return sorted(ROLE_PERMISSIONS.get(normalize_role(role), ROLE_PERMISSIONS["usuario"]))


def role_has_permission(role: str | None, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(normalize_role(role), ROLE_PERMISSIONS["usuario"])
