"""Catálogo UX del Centro de Permisos (sin cambiar grupos ni ACL)."""

PERMISSIONS_UX_CATEGORIES = (
    {"key": "finance", "label": "FINANZAS", "sequence": 10},
    {"key": "operations", "label": "OPERACIONES", "sequence": 20},
    {"key": "consulting", "label": "CONSULTA", "sequence": 30},
    {"key": "erp_admin", "label": "ADMINISTRACIÓN DEL ERP", "sequence": 40},
    {"key": "justech_internal", "label": "USO INTERNO JUSTECH", "sequence": 50},
)

PERMISSIONS_UX_ITEMS = (
    {
        "code": "accounting",
        "label": "Contabilidad",
        "category_key": "finance",
        "tooltip": (
            "Permite acceder a diarios, asientos contables, reportes financieros "
            "y configuración contable."
        ),
        "protected": False,
        "privilege_xmlid": "account.res_groups_privilege_accounting",
        "levels": (
            ("none", "Ninguno", ()),
            ("user", "Usuario", ("account.group_account_user",)),
            ("manager", "Administrador", ("account.group_account_manager",)),
        ),
    },
    {
        "code": "bank",
        "label": "Banco",
        "category_key": "finance",
        "tooltip": (
            "Permite administrar cuentas bancarias, conciliaciones y pagos."
        ),
        "protected": False,
        "privilege_xmlid": "account.res_group_privilege_accounting_bank",
        "levels": (
            ("none", "Ninguno", ()),
            ("on", "Activo", ("account.group_validate_bank_account",)),
        ),
    },
    {
        "code": "multicurrency",
        "label": "Multimoneda",
        "category_key": "finance",
        "tooltip": (
            "Permite configurar monedas, tasas de cambio y precios comerciales."
        ),
        "protected": False,
        "privilege_xmlid": "justech_multicurrency.res_groups_privilege_justech_multicurrency",
        "levels": (
            ("none", "Ninguno", ()),
            ("user", "Usuario", ("justech_multicurrency.group_justech_multicurrency_user",)),
            (
                "manager",
                "Administrador",
                ("justech_multicurrency.group_justech_multicurrency_manager",),
            ),
        ),
    },
    {
        "code": "purchase",
        "label": "Compras",
        "category_key": "operations",
        "tooltip": (
            "Permite crear solicitudes, órdenes de compra y administrar proveedores."
        ),
        "protected": False,
        "privilege_xmlid": "purchase.res_groups_privilege_purchase",
        "levels": (
            ("none", "Ninguno", ()),
            ("user", "Usuario", ("purchase.group_purchase_user",)),
            ("manager", "Administrador", ("purchase.group_purchase_manager",)),
        ),
    },
    {
        "code": "inventory",
        "label": "Inventario",
        "category_key": "operations",
        "tooltip": (
            "Permite administrar almacenes, existencias y movimientos."
        ),
        "protected": False,
        "privilege_xmlid": "stock.res_groups_privilege_inventory",
        "levels": (
            ("none", "Ninguno", ()),
            ("user", "Usuario", ("stock.group_stock_user",)),
            ("manager", "Administrador", ("stock.group_stock_manager",)),
        ),
    },
    {
        "code": "dashboard",
        "label": "Tablero",
        "category_key": "consulting",
        "tooltip": (
            "Permite visualizar indicadores y paneles gerenciales."
        ),
        "protected": False,
        "privilege_xmlid": "spreadsheet_dashboard.res_groups_privilege_dashboard",
        "levels": (
            ("none", "Ninguno", ()),
            ("on", "Activo", ("spreadsheet_dashboard.group_dashboard_manager",)),
        ),
    },
    {
        "code": "audit",
        "label": "Auditoría",
        "category_key": "consulting",
        "tooltip": (
            "Permite consultar el historial de cambios del sistema."
        ),
        "protected": False,
        "privilege_xmlid": "justech_global_audit_log.res_groups_privilege_justech_audit",
        "levels": (
            ("none", "Ninguno", ()),
            ("user", "Usuario", ("justech_global_audit_log.group_audit_user",)),
            (
                "manager",
                "Administrador",
                ("justech_global_audit_log.group_justech_audit_manager",),
            ),
        ),
    },
    {
        "code": "governance",
        "label": "Hellenia Governance",
        "category_key": "erp_admin",
        "tooltip": (
            "Permite administrar configuraciones corporativas del ERP."
        ),
        "protected": False,
        "privilege_xmlid": "hellenia_governance.res_groups_privilege_governance",
        "levels": (
            ("none", "Ninguno", ()),
            ("user", "Usuario", ("hellenia_governance.group_governance_user",)),
            ("manager", "Administrador", ("hellenia_governance.group_governance_manager",)),
        ),
    },
    {
        "code": "justech_admin",
        "label": "Justech Admin",
        "category_key": "justech_internal",
        "tooltip": (
            "Herramientas exclusivas del personal técnico de Justech."
        ),
        "protected": True,
        "privilege_xmlid": "justech_admin.res_groups_privilege_justech_admin",
        "levels": (
            ("none", "Ninguno", ()),
            ("on", "Activo", ("justech_admin.group_justech_admin_user",)),
        ),
    },
    {
        "code": "justech_platform",
        "label": "Justech Platform",
        "category_key": "justech_internal",
        "tooltip": (
            "Herramientas internas de licenciamiento y administración de la plataforma."
        ),
        "protected": True,
        "privilege_xmlid": "justech_modules.res_groups_privilege_justech",
        "levels": (
            ("none", "Ninguno", ()),
            ("user", "Usuario", ("justech_modules.group_justech_license_user",)),
            ("manager", "Administrador", ("justech_modules.group_justech_license_manager",)),
            (
                "internal",
                "Administrador interno",
                ("justech_modules.group_justech_internal_admin",),
            ),
        ),
    },
)

PROTECTED_PERMISSION_CODES = frozenset(
    item["code"] for item in PERMISSIONS_UX_ITEMS if item.get("protected")
)
