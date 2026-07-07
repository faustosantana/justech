{
    "name": "Justech Dominican NCF",
    "version": "19.0.1.6.0",
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
    "justech_register": {
        "module_code": "justech_l10n_do_ncf",
        "module_name": "Justech Dominican NCF",
        "version": "19.0.1.6.0",
        "category": "fiscal",
        "country": "DO",
        "localization": "l10n_do",
        "description": "NCF ranges, assignment and validation",
        "dependencies": ["justech_l10n_do_base"],
        "always_enabled": True,
        "required_module": True,
        "features": [
            {"code": "l10n_do_ncf", "name": "DO NCF Management"},
        ],
    },
}
