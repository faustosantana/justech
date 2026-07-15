{
    "name": "Justech Security UX — Permisos Enterprise",
    "version": "19.0.2.0.0",
    "category": "Administration",
    "summary": "Administración enterprise de permisos sobre res.groups (sin ACL paralela)",
    "description": """
Capa UX Enterprise para administrar usuarios por responsabilidades:

- Navegación por áreas (Comercial, Compras, Inventario, Finanzas, Fiscal, etc.)
- Tarjetas de roles con capacidades
- Acciones operativas con tooltips en lenguaje de negocio
- Permisos Avanzados (res.groups técnicos) solo para Administrador del Sistema

La fuente de verdad sigue siendo res.groups.
    """,
    "author": "Justech",
    "website": "https://justech.do",
    "depends": [
        "base",
        "account",
        "purchase",
        "sale",
        "stock",
        "crm",
        "hr",
        "l10n_do_accounting",
        "justech_l10n_do_base",
        "justech_fiscal_admin",
        "justech_ecf_core",
        "justech_l10n_do_payments_withholding",
        "justech_warranty",
        "justech_admin_center",
    ],
    "data": [
        "views/res_users_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "justech_security_ux/static/src/scss/operational_permissions.scss",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "justech_security_ux",
        "module_name": "Justech Security UX",
        "version": "19.0.2.0.0",
        "category": "platform",
        "country": "DO",
        "description": "Permisos enterprise UX sobre grupos Odoo",
        "dependencies": ["justech_admin_center", "justech_l10n_do_base"],
        "always_enabled": False,
        "required_module": False,
    },
}
