{
    "name": "Hellenia UX",
    "version": "19.0.1.2.0",
    "category": "Hidden",
    "summary": "Localización visual RD y experiencia de usuario Hellenia",
    "description": """
Mejoras UX upgrade-safe (Fase 17):

- Etiquetas en español en formularios contables y fiscales
- Bloque NCF visual dominicano
- Anulación NCF con wizard y banda DOCUMENTO ANULADO
- Wizard de pagos mejorado con documentos pendientes
- Retenciones RD en facturas de compra
- Campos método de pago (tarjeta, cheque)
- Sin QR en PDF (no e-CF)
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "hellenia_ui",
        "hellenia_account",
        "hellenia_reports",
        "justech_l10n_do_ncf",
        "justech_l10n_do_base",
        "justech_l10n_do_reports",
        "sale_management",
        "purchase",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/justech_do_ncf_void_wizard_views.xml",
        "views/account_move_fiscal_views.xml",
        "views/account_move_invoice_form_phase28_views.xml",
        "views/account_move_form_views.xml",
        "views/account_payment_register_views.xml",
        "views/account_payment_views.xml",
        "views/account_move_withholding_views.xml",
        "views/res_company_views.xml",
        "views/ncf_range_views.xml",
        "views/fiscal_security_labels.xml",
        "data/post_init.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hellenia_ux/static/src/scss/hellenia_ux.scss",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "justech_register": {
        "module_code": "hellenia_ux",
        "module_name": "Hellenia UX",
        "version": "19.0.1.2.0",
        "category": "ux",
        "country": "DO",
        "description": "Dominican visual UX and fiscal form improvements",
        "dependencies": ["hellenia_ui", "hellenia_account"],
        "always_enabled": True,
        "features": [{"code": "hellenia_ux", "name": "Hellenia UX"}],
    },
}
