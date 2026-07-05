{
    "name": "Justech Modules",
    "version": "19.0.1.2.0",
    "category": "Justech/Platform",
    "summary": "Motor de licencias y catálogo comercial Justech",
    "description": """
Justech platform licensing engine.

F31.1.2 hardening: hashed license keys, ormcache, Odoo 19 constraints,
expired license enforcement, max_users seats.
    """,
    "author": "Justech",
    "website": "https://justech.cloud",
    "depends": ["base", "mail"],
    "data": [
        "security/justech_modules_security.xml",
        "security/ir.model.access.csv",
        "views/justech_module_views.xml",
        "views/justech_feature_views.xml",
        "views/justech_license_views.xml",
        "views/justech_activation_key_views.xml",
        "views/justech_license_audit_views.xml",
        "views/menu.xml",
    ],
    "pre_init_hook": "pre_init_hook",
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
