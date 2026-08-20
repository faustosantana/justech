{
    "name": "Justech DGCP Bridge",
    "version": "19.0.1.2.0",
    "category": "Sales/CRM",
    "summary": "DGCP líneas solicitadas en CRM + trazabilidad JAIOS ↔ cotización",
    "depends": ["crm", "sale_crm", "purchase", "stock", "account", "mail", "product"],
    "data": [
        "security/ir.model.access.csv",
        "views/dgcp_opportunity_line_views.xml",
        "views/crm_lead_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
