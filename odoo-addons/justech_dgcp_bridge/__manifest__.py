{
    "name": "Justech DGCP Bridge",
    "version": "19.0.1.3.0",
    "category": "Sales/CRM",
    "summary": "Visibilidad simple DGCP/JAIOS en CRM (licitación, responsable, productos)",
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
