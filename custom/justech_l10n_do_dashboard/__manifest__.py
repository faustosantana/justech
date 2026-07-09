{
    "name": "Justech Dominican Fiscal Dashboard",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Fiscal dashboard shell — KPIs and health monitoring (Justech)",
    "description": """
Fiscal dashboard module for Dominican Republic — Justech product layer.

Sprint 1: structure only (no complex widgets yet).
Future: KPIs, sequence health, alerts, diagnostic wizard.
    """,
    "author": "Justech",
    "website": "https://justech.do",
    "depends": [
        "justech_l10n_do_base",
        "justech_l10n_do_ncf",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/fiscal_dashboard_data.xml",
        "views/fiscal_dashboard_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "justech_l10n_do_dashboard",
        "module_name": "Justech Dominican Fiscal Dashboard",
        "version": "19.0.1.0.0",
        "category": "fiscal",
        "country": "DO",
        "localization": "l10n_do",
        "description": "Fiscal dashboard and health monitoring",
        "dependencies": ["justech_l10n_do_base", "justech_l10n_do_ncf"],
        "always_enabled": False,
        "required_module": False,
        "features": [
            {"code": "l10n_do_dashboard", "name": "DO Fiscal Dashboard"},
        ],
    },
}
