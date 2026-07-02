{
    "name": "Justech Report Design",
    "version": "19.0.4.0.1",
    "category": "Reporting",
    "summary": "Cotización y factura fiscal Hellenia — diseño Justech QWeb+SCSS",
    "description": """
Diseño PDF Hellenia / Justech — Odoo 19.

Cotización (Fase 24.2):
- sale.action_report_saleorder → reporte Justech oficial

Factura fiscal (Fase 26):
- account.account_invoices → reporte Justech oficial
- Respaldo estándar sin menú Imprimir (rollback técnico)
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "sale",
        "account",
        "hellenia_reports",
    ],
    "data": [
        "data/paperformat_data.xml",
        "data/quotation_terms_default.xml",
        "views/res_company_views.xml",
        "views/sale_order_views.xml",
        "report/quotation/hellenia_quotation_template.xml",
        "report/invoice/justech_invoice_template.xml",
        "report/invoice/justech_invoice_preview.xml",
        "data/report_action_data.xml",
        "data/report_invoice_action_data.xml",
        "data/report_official_data.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "justech_report_design/static/src/scss/hellenia_quotation.scss",
            "justech_report_design/static/src/scss/hellenia_invoice.scss",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
