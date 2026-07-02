{
    "name": "Justech Report Design",
    "version": "19.0.3.6.0",
    "category": "Reporting",
    "summary": "Cotización y factura fiscal Hellenia — diseño Justech QWeb+SCSS",
    "description": """
Diseño PDF Hellenia / Justech — Odoo 19.

Cotización (Fase 24.2B):
- sale.action_report_saleorder → reporte Justech
- Condiciones empresa → sale.order.note

Factura fiscal (Fase 25):
- Reporte paralelo: Justech PDF — Factura
- No reemplaza account.report_invoice
- NCF, tipo comprobante, ITBIS, retenciones desde campos reales
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "sale",
        "account",
    ],
    "data": [
        "data/paperformat_data.xml",
        "data/quotation_terms_default.xml",
        "views/res_company_views.xml",
        "views/sale_order_views.xml",
        "report/quotation/hellenia_quotation_template.xml",
        "report/invoice/justech_invoice_template.xml",
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
