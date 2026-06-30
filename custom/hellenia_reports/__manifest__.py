{
    "name": "Hellenia Reports",
    "version": "19.0.1.0.0",
    "category": "Reporting",
    "summary": "Formatos corporativos PDF Hellenia",
    "description": """
Formatos visuales corporativos para documentos comerciales Hellenia.

- Layout corporativo único (external_layout_hellenia)
- Cotización, pedido, factura, NC, compras, entregas y recepciones
- Herencia QWeb upgrade-safe
    """,
    "author": "Justech",
    "website": "https://hellenia.cloud",
    "depends": [
        "hellenia_base",
        "sale",
        "account",
        "purchase",
        "stock",
        "justech_l10n_do_ncf",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/paperformat_data.xml",
        "report/layout_templates.xml",
        "data/report_layout_data.xml",
        "report/report_sale_order.xml",
        "report/report_invoice.xml",
        "report/report_purchase.xml",
        "report/report_stock.xml",
        "data/report_actions_data.xml",
        "data/company_layout_data.xml",
        "views/res_company_views.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "hellenia_reports/static/src/scss/hellenia_reports.scss",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
