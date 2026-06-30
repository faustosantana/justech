{
    "name": "Justech Dominican Fiscal Reports",
    "version": "19.0.1.4.0",
    "category": "Accounting/Localizations/Reporting",
    "summary": "DGII reports 606, 607, 608 — exportador piloto 606",
    "description": """
Dominican DGII fiscal reports for Justech.

- Format 606 (purchases) — exportador Excel DGII piloto
- Format 607 (sales)
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
        "views/fiscal_report_views.xml",
        "wizard/fiscal_report_wizard_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
