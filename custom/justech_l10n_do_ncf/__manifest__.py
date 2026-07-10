{
    "name": "Justech Dominican NCF",
    "version": "19.0.2.3.1",
    "category": "Accounting/Localizations",
    "summary": "NCF ranges, assignment and validation (Dominican Republic)",
    "description": """
NCF management for Dominican Republic — Justech Enterprise layer.

- NCF ranges and consumption audit
- Automatic NCF on customer invoices
- Fiscal Administration Center
- Fiscal diagnostic (read-only)
- Duplicate detection v2.0
    """,
    "author": "Justech",
    "website": "https://justech.do",
    "depends": [
        "justech_l10n_do_base",
        "account_debit_note",
        "sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/justech_l10n_do_ncf_rules.xml",
        "views/fiscal_admin_views.xml",
        "views/fiscal_diagnostic_views.xml",
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
        "version": "19.0.2.3.1",
        "category": "fiscal",
        "country": "DO",
        "localization": "l10n_do",
        "description": "NCF ranges, assignment, admin center and diagnostics",
        "dependencies": ["justech_l10n_do_base"],
        "always_enabled": True,
        "required_module": True,
        "features": [
            {"code": "l10n_do_ncf", "name": "DO NCF Management"},
            {"code": "l10n_do_ncf_admin", "name": "DO Fiscal Admin Center"},
        ],
    },
}
