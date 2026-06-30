{
    "name": "Justech Dominican Fiscal Base",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations",
    "summary": "Base fiscal configuration for Dominican Republic (Justech)",
    "description": """
Dominican fiscal base layer for Justech localization.

- Fiscal document types (NCF)
- Company and journal fiscal settings
- Partner RNC basic validation
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "account",
        "contacts",
        "l10n_do",
    ],
    "data": [
        "security/justech_l10n_do_security.xml",
        "security/ir.model.access.csv",
        "data/fiscal_document_type_data.xml",
        "views/fiscal_document_type_views.xml",
        "views/res_company_views.xml",
        "views/res_partner_views.xml",
        "views/account_journal_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
