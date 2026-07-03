{
    "name": "Justech Dominican NCF",
    "version": "19.0.1.5.2",
    "category": "Accounting/Localizations",
    "summary": "NCF ranges, assignment and validation (Dominican Republic)",
    "description": """
NCF management for Dominican Republic — Justech MVP.

- NCF ranges and consumption audit
- Automatic NCF on customer invoices
- B11/B13 on purchase documents
- Validations (duplicate, expired, depleted)
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "justech_l10n_do_base",
        "account_debit_note",
        "sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/justech_l10n_do_ncf_rules.xml",
        "views/ncf_range_views.xml",
        "views/ncf_consumption_views.xml",
        "views/account_move_views.xml",
        "views/sale_order_views.xml",
        "views/menu.xml",
        "report/report_invoice.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
