{
    "name": "Justech Security UX — Permisos Operativos",
    "version": "19.0.1.0.0",
    "category": "Administration",
    "summary": "Capa operativa de permisos sobre res.groups (sin ACL paralela)",
    "description": """
Interfaz amigable «Permisos Operativos» en la ficha de usuario.

- Organiza capacidades por módulo con tooltips.
- Sincronización bidireccional con res.groups existentes.
- No crea ACL, ir.rule ni grupos nuevos.
- Preserva la pestaña técnica «Permisos de acceso (Avanzado)».
    """,
    "author": "Justech",
    "website": "https://justech.do",
    "depends": [
        "base",
        "account",
        "purchase",
        "sale",
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
        "version": "19.0.1.0.0",
        "category": "platform",
        "country": "DO",
        "description": "Permisos operativos UX sobre grupos Odoo",
        "dependencies": ["justech_admin_center", "justech_l10n_do_base"],
        "always_enabled": False,
        "required_module": False,
    },
}
