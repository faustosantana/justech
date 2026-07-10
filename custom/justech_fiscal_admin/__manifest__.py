{
    "name": "Justech Fiscal Administration Center",
    "version": "19.0.1.1.0",
    "summary": "Enterprise fiscal stack administration — settings, health, feature flags",
    "description": """
Centro de Administración Fiscal Justech (Enterprise).

- Estado del stack fiscal completo
- Health check y diagnóstico
- Feature flags funcionales (sin instalar/desinstalar módulos)
- Vista multiempresa del motor NCF, Provider, DGII, Dashboard
    """,
    "author": "Justech",
    "website": "https://justech.do",
    "depends": [
        "base_setup",
        "justech_l10n_do_base",
        "justech_l10n_do_ncf",
    ],
    "data": [
        "security/justech_fiscal_admin_security.xml",
        "security/ir.model.access.csv",
        "data/justech_fiscal_feature_flag_data.xml",
        "views/justech_fiscal_admin_center_views.xml",
        "views/justech_fiscal_feature_flag_views.xml",
        "views/justech_res_config_settings_views.xml",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "justech_fiscal_admin/static/src/scss/fiscal_admin.scss",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "justech_fiscal_admin",
        "module_name": "Justech Fiscal Administration Center",
        "version": "19.0.1.1.0",
        "country": "DO",
        "description": "Enterprise fiscal administration center",
        "dependencies": ["justech_l10n_do_ncf", "justech_l10n_do_reports"],
        "features": [
            {"code": "fiscal_admin_center", "name": "Fiscal Admin Center"},
            {"code": "fiscal_feature_flags", "name": "Fiscal Feature Flags"},
        ],
    },
}
