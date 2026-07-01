{
    "name": "Hellenia Reports",
    "version": "19.0.1.3.1",
    "category": "Reporting",
    "summary": "Formatos corporativos PDF Hellenia",
    "description": """
Formatos visuales corporativos para documentos comerciales Hellenia.

- Layout corporativo único (external_layout_hellenia) — identidad #3E4827
- Cotización, pedido, factura, NC, ND, compras, entregas y recepciones
- Recibo de pago, estados de cuenta cliente/proveedor
- Herencia QWeb upgrade-safe (solo presentación)
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "hellenia_base",
        "hellenia_account",
        "sale",
        "account",
        "purchase",
        "stock",
        "justech_l10n_do_ncf",
        "account_reports",
        "account_followup",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/paperformat_data.xml",
        "report/layout_templates.xml",
        "data/report_layout_data.xml",
        "data/quotation_terms_default.xml",
        "report/report_sale_quotation.xml",
        "report/report_sale_order.xml",
        "report/report_invoice.xml",
        "report/report_purchase.xml",
        "report/report_stock.xml",
        "report/report_payment_receipt.xml",
        "report/report_account_statements.xml",
        "data/report_actions_data.xml",
        "data/company_layout_data.xml",
        "views/res_company_views.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "hellenia_reports/static/src/scss/hellenia_reports.scss",
        ],
        "account_reports.assets_pdf_export": [
            "hellenia_reports/static/src/scss/hellenia_reports.scss",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
