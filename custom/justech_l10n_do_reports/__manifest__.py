{
    "name": "Justech Dominican Fiscal Reports",
    "version": "19.0.1.12.2",
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
        "hellenia_account",
    ],
    "external_dependencies": {
        "python": ["xlsxwriter"],
    },
    "data": [
        "security/ir.model.access.csv",
        "security/justech_l10n_do_reports_rules.xml",
        "views/dgii_report_review_views.xml",
        "views/dgii_report_pending_tray_views.xml",
        "views/fiscal_report_views.xml",
        "wizard/fiscal_report_wizard_views.xml",
        "wizard/dgii_export_blocker_wizard_views.xml",
        "views/menu.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
