{
    "name": "Justech Report Design",
    "version": "19.0.6.0.0",
    "category": "Reporting",
    "summary": "Cotización, factura y conduce Hellenia — diseño Justech QWeb+SCSS",
    "description": """
Diseño PDF Hellenia / Justech — Odoo 19.

Cotización (Fase 24.2):
- sale.action_report_saleorder → reporte Justech oficial

Factura fiscal (Fase 26):
- account.account_invoices → reporte Justech oficial

Conduce de Entrega (Fase 26E):
- Modelo justech.delivery.note con secuencia COND/AÑO/#####
- Botón Crear Conduce + smart button con contador real
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "mail",
        "sale",
        "sale_stock",
        "stock",
        "account",
        "hellenia_reports",
    ],
    "data": [
        "data/paperformat_data.xml",
        "data/justech_delivery_note_sequence.xml",
        "security/ir.model.access.csv",
        "data/quotation_terms_default.xml",
        "views/res_company_views.xml",
        "views/sale_order_views.xml",
        "views/sale_order_delivery_views.xml",
        "views/account_move_delivery_views.xml",
        "views/stock_picking_delivery_views.xml",
        "views/justech_delivery_note_views.xml",
        "report/quotation/hellenia_quotation_template.xml",
        "report/invoice/justech_invoice_template.xml",
        "report/invoice/justech_invoice_preview.xml",
        "report/delivery/justech_delivery_template.xml",
        "data/report_action_data.xml",
        "data/report_invoice_action_data.xml",
        "data/report_delivery_action_data.xml",
        "data/report_official_data.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "justech_report_design/static/src/scss/hellenia_quotation.scss",
            "justech_report_design/static/src/scss/hellenia_invoice.scss",
            "justech_report_design/static/src/scss/hellenia_delivery.scss",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
