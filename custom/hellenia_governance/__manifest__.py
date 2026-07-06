{
    "name": "Hellenia Governance",
    "version": "19.0.1.1.0",
    "category": "Justech/Platform",
    "summary": "Permisos funcionales, roles y auditoría operativa",
    "description": """
Capa de gobierno funcional Hellenia (F31.2).

Permisos, roles, perfiles de usuario, políticas de features/menú y auditoría.
Consume justech_modules para licencias — no las gestiona.
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": ["base", "mail", "web", "justech_modules"],
    "data": [
        "security/hellenia_governance_security.xml",
        "security/ir.model.access.csv",
        "data/hellenia_permission_data.xml",
        "data/hellenia_role_data.xml",
        "views/hellenia_permission_views.xml",
        "views/hellenia_role_views.xml",
        "views/hellenia_user_profile_views.xml",
        "views/hellenia_feature_policy_views.xml",
        "views/hellenia_menu_policy_views.xml",
        "views/hellenia_governance_audit_views.xml",
        "views/hellenia_governance_protected_actions.xml",
        "views/menu.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "hellenia_governance",
        "module_name": "Hellenia Governance",
        "version": "19.0.1.1.0",
        "category": "platform",
        "description": "Functional permissions and governance",
        "dependencies": ["justech_modules"],
        "always_enabled": True,
        "features": [{"code": "hellenia_governance", "name": "Hellenia Governance"}],
    },
}
