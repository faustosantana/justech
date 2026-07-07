{
    "name": "Justech Admin",
    "version": "19.0.2.14.2",
    "category": "Justech/Platform",
    "summary": "Centro de Control Justech Enterprise",
    "description": """
F31.5: Rediseño definitivo del Centro de Control — consola comercial Enterprise.
    """,
    "author": "Justech",
    "website": "https://justech.cloud",
    "depends": ["base", "base_setup", "web", "mail", "justech_modules", "hellenia_governance"],
    "data": [
        "security/justech_admin_security.xml",
        "security/ir.model.access.csv",
        "views/justech_admin_protected_actions.xml",
        "views/justech_control_center_views.xml",
        "views/justech_license_admin_wizard_views.xml",
        "views/justech_client_module_views.xml",
        "views/justech_res_config_settings_views.xml",
        "views/justech_admin_dashboard_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "justech_admin/static/src/scss/control_center.scss",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "justech_admin",
        "module_name": "Justech Admin",
        "version": "19.0.2.13.2",
        "category": "platform",
        "description": "Enterprise Control Center",
        "dependencies": ["justech_modules", "hellenia_governance"],
        "always_enabled": True,
        "features": [{"code": "justech_admin", "name": "Justech Admin"}],
    },
}
