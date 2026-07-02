{
    "name": "Justech Report Design",
    "version": "19.0.2.1.0",
    "category": "Reporting",
    "summary": "Cotización oficial Hellenia — diseño Justech QWeb+SCSS (portable)",
    "description": """
Cotización PDF oficial Hellenia / Justech — Odoo 19.

- Diseño QWeb + SCSS aprobado (Fase 24.2B)
- sale.action_report_saleorder → reporte Justech
- Condiciones empresa → sale.order.note al crear
- PDF imprime exactamente doc.note
- Respaldo: Cotización en PDF (estándar Odoo)
- Instalable con solo el módulo sale (sin hellenia_reports obligatorio)
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "sale",
    ],
    "data": [
        "data/paperformat_data.xml",
        "data/quotation_terms_default.xml",
        "views/res_company_views.xml",
        "views/sale_order_views.xml",
        "report/quotation/hellenia_quotation_template.xml",
        "data/report_action_data.xml",
        "data/report_official_data.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "justech_report_design/static/src/scss/hellenia_quotation.scss",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
