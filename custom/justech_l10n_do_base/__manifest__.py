{
    "name": "Justech Dominican Fiscal Base",
    "version": "19.0.1.19.0",
    "category": "Accounting/Localizations",
    "summary": "Base fiscal configuration for Dominican Republic (Justech)",
    "description": """
Dominican fiscal base layer for Justech localization.

- Fiscal document types (NCF)
- Company and journal fiscal settings
- Partner RNC basic validation
- Padrón DGII: importación, historial, actualización automática
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "account",
        "contacts",
        "l10n_do",
        "l10n_do_accounting",
        "mail",
    ],
    "data": [
        "security/justech_l10n_do_security.xml",
        "security/ir.model.access.csv",
        "security/justech_l10n_do_rules.xml",
        "data/fiscal_document_type_data.xml",
        "data/rnc_padron_cron_data.xml",
        "views/fiscal_document_type_views.xml",
        "views/res_company_views.xml",
        "views/res_partner_views.xml",
        "views/account_journal_views.xml",
        "views/rnc_padron_admin_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "justech_l10n_do_base",
        "module_name": "Justech Dominican Fiscal Base",
        "version": "19.0.1.17.0",
        "category": "fiscal",
        "country": "DO",
        "localization": "l10n_do",
        "description": "Base fiscal configuration for Dominican Republic",
        "dependencies": [],
        "always_enabled": True,
        "required_module": True,
        "features": [
            {"code": "l10n_do_base", "name": "DO Fiscal Base"},
            {"code": "rnc_padron_admin", "name": "Padrón DGII Admin"},
        ],
    },
}
