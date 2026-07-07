{
    "name": "Justech Global Audit Log",
    "version": "19.0.1.0.0",
    "category": "Justech/Platform",
    "summary": "Auditoría global configurable multiempresa para Odoo 19",
    "description": """
Auditoría global Justech — producto enterprise.

- Activación por modelo, operación, empresa y usuario
- Escritura diferida post-commit para mínimo impacto en performance
- Retención automática y limpieza programada
- Exclusión de campos sensibles y modelos técnicos
- Integración opcional con justech_modules y hellenia_governance
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/justech_audit_security.xml",
        "security/ir.model.access.csv",
        "data/audit_field_exclude_data.xml",
        "data/audit_retention_data.xml",
        "data/audit_cron.xml",
        "views/audit_policy_views.xml",
        "views/audit_rule_views.xml",
        "views/audit_field_exclude_views.xml",
        "views/audit_user_exclude_views.xml",
        "views/audit_log_views.xml",
        "views/audit_retention_views.xml",
        "views/audit_dashboard_views.xml",
        "wizards/audit_export_wizard_views.xml",
        "views/menu.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "justech_register": {
        "module_code": "justech_global_audit_log",
        "module_name": "Justech Global Audit Log",
        "version": "19.0.1.0.0",
        "category": "platform",
        "description": "Enterprise global audit log for Odoo",
        "dependencies": [],
        "always_enabled": False,
        "features": [
            {"code": "global_audit", "name": "Global Audit Log"},
        ],
    },
}
