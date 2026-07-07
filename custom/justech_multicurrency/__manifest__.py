{
    "name": "Justech Multimoneda",
    "version": "19.0.2.0.0",
    "category": "Justech/Platform",
    "summary": "Capa comercial multimoneda sobre el motor estándar Odoo",
    "description": """
Motor Corporativo Multimoneda Justech.

Capa comercial sobre el motor estándar Odoo 19:
- Precio de venta/compra con moneda en el producto
- Sincronización automática con list_price, standard_price y listas de precios
- Política comercial por empresa
- Dashboard y administración de tasas
- Listas de precios ocultas para usuarios comerciales

No modifica contabilidad, NCF, DGII, PDFs ni COA.
    """,
    "author": "Justech",
    "website": "https://justech.cloud",
    "license": "LGPL-3",
    "depends": [
        "base",
        "product",
        "sale",
        "purchase",
        "justech_modules",
    ],
    "data": [
        "security/justech_multicurrency_security.xml",
        "security/ir.model.access.csv",
        "views/multicurrency_policy_views.xml",
        "views/multicurrency_dashboard_views.xml",
        "views/res_currency_rate_views.xml",
        "views/product_template_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "justech_multicurrency/static/src/scss/dashboard.scss",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "justech_register": {
        "module_code": "justech_multicurrency",
        "module_name": "Justech Multimoneda",
        "version": "19.0.2.0.0",
        "category": "platform",
        "description": "Corporate multicurrency commercial policy engine",
        "dependencies": ["justech_modules"],
        "always_enabled": False,
        "features": [
            {"code": "multicurrency", "name": "Motor Multimoneda Justech"},
        ],
    },
}
