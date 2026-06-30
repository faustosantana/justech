{
    "name": "Justech Dominican Fiscal Reports",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations/Reporting",
    "summary": "DGII reports 606, 607, 608 — basic MVP",
    "description": """
Basic Dominican DGII fiscal reports for Justech MVP.

- Format 606 (purchases)
- Format 607 (sales)
- Format 608 (voided NCF)
- CSV and Excel export
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "justech_l10n_do_ncf",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/fiscal_report_views.xml",
        "wizard/fiscal_report_wizard_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
