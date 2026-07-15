{
    "name": "Justech Security UX — Permisos Justech",
    "version": "19.0.3.1.1",
    "category": "Administration",
    "summary": "Interfaz por módulos sobre res.groups reales (sin ACL paralela)",
    "description": """
Pestaña «Permisos Justech»: navegación compacta por módulos, buscador,
resumen y compatibilidad tema claro/oscuro. Fuente de verdad: res.groups.

«Permisos Avanzados» conserva la matriz técnica estándar.

No crea ACL, Record Rules ni grupos nuevos.
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
            "justech_security_ux/static/src/xml/permissions_nav.xml",
            "justech_security_ux/static/src/js/permissions_nav.js",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "justech_security_ux",
        "module_name": "Justech Security UX",
        "version": "19.0.3.1.1",
        "category": "platform",
        "country": "DO",
        "description": "Permisos Justech compactos por módulos sobre grupos Odoo",
        "dependencies": ["justech_admin_center", "justech_l10n_do_base"],
        "always_enabled": False,
        "required_module": False,
    },
}
