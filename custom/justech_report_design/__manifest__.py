{
    "name": "Justech Report Design",
    "version": "19.0.1.0.5",
    "category": "Reporting",
    "summary": "Diseño HTML/QWeb cotización Hellenia — módulo limpio TEST",
    "description": """
Reporte paralelo de cotización Hellenia con QWeb + SCSS en assets PDF.

- No modifica sale.report_saleorder_document
- Estilos en web.report_assets_common (wkhtmltopdf)
- Paperformat dedicado carta compacto
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "sale",
    ],
    "data": [
        "data/paperformat_data.xml",
        "report/quotation/hellenia_quotation_template.xml",
        "data/report_action_data.xml",
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
