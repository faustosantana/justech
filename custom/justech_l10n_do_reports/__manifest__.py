{
    "name": "Justech Dominican Fiscal Reports",
    "version": "19.0.1.20.0",
    "category": "Accounting/Localizations/Reporting",
    "summary": "DGII reports 606–609, 623 — exportadores oficiales",
    "description": """
Dominican DGII fiscal reports for Justech.

- Format 606 (purchases) — exportador Excel DGII
- Format 607 (sales) — exportador Excel DGII
- Format 608 (voided NCF)
- Validation wizard and export history
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "justech_l10n_do_ncf",
        "justech_fiscal_admin",
    ],
    "external_dependencies": {
        "python": ["xlsxwriter"],
    },
    "data": [
        "security/ir.model.access.csv",
        "security/justech_l10n_do_reports_rules.xml",
        "views/fiscal_report_views.xml",
        "views/dgii_report_review_views.xml",
        "views/dgii_report_pending_tray_views.xml",
        "views/fiscal_report_actions.xml",
        "wizard/fiscal_report_wizard_views.xml",
        "wizard/dgii_export_blocker_wizard_views.xml",
        "views/menu.xml",
        "views/dgii_tax_classification_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "justech_l10n_do_reports",
        "module_name": "Justech Dominican Fiscal Reports",
        "version": "19.0.1.19.0",
        "category": "reports",
        "country": "DO",
        "localization": "l10n_do",
        "description": "DGII reports 606, 607, 608, 623",
        "dependencies": ["justech_l10n_do_ncf"],
        "always_enabled": True,
        "required_module": True,
        "features": [
            {"code": "l10n_do_reports", "name": "DO DGII Reports"},
        ],
    },
}
