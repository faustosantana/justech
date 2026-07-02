{
    "name": "Justech Report Design",
    "version": "19.0.2.0.0",
    "category": "Reporting",
    "summary": "Cotización oficial Hellenia — diseño Justech QWeb+SCSS",
    "description": """
Cotización oficial Hellenia (Fase 24.2).

- sale.action_report_saleorder apunta al diseño Justech
- Condiciones desde res.company → sale.order.note al crear
- PDF imprime exactamente doc.note (sin texto quemado en XML)
- Respaldo: action_report_saleorder_backup (reporte estándar)
- Estilos en web.report_assets_common (wkhtmltopdf)
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "sale",
        "hellenia_reports",
    ],
    "data": [
        "data/paperformat_data.xml",
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
