{
    "name": "Justech Modules",
    "version": "19.0.1.1.0",
    "category": "Justech/Platform",
    "summary": "Motor de licencias y catálogo comercial Justech",
    "description": """
Justech platform licensing engine.

- Module and feature catalog
- Commercial module dependencies (DAG)
- License and activation keys
- Public API v1: is_active, require_active, get_feature, validate_license,
  activate_feature, deactivate_feature, check_dependencies
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
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
