{
    "name": "Justech Admin",
    "version": "19.0.1.0.0",
    "category": "Justech/Platform",
    "summary": "Centro de Control administrativo Justech",
    "description": """
Panel administrativo (F31.3). Presenta datos de justech_modules y hellenia_governance.
Sin lógica de negocio duplicada.
    """,
    "author": "Justech",
    "website": "https://justech.cloud",
    "depends": ["base", "web", "mail", "justech_modules", "hellenia_governance"],
    "data": [
        "security/justech_admin_security.xml",
        "security/ir.model.access.csv",
        "views/justech_admin_dashboard_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "justech_admin",
        "module_name": "Justech Admin",
        "version": "19.0.1.0.0",
        "category": "platform",
        "description": "Administrative control center",
        "dependencies": ["justech_modules", "hellenia_governance"],
        "always_enabled": True,
        "features": [{"code": "justech_admin", "name": "Justech Admin"}],
    },
}
