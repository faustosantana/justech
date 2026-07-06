from odoo import fields, models


class JustechCommercialProduct(models.Model):
    _name = "justech.commercial.product"
    _description = "Justech Commercial Product Catalog"
    _order = "sequence, name"

    code = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    description = fields.Text()
    icon = fields.Char(default="fa-cube")
    category = fields.Selection(
        [
            ("fiscal", "Fiscal"),
            ("sales", "Ventas"),
            ("purchase", "Compras"),
            ("inventory", "Inventario"),
            ("pos", "Punto de Venta"),
            ("crm", "CRM"),
            ("reports", "Reportes"),
            ("assets", "Activos"),
            ("hr", "RRHH"),
            ("platform", "Plataforma"),
            ("integration", "Integración"),
            ("ai", "Inteligencia Artificial"),
        ],
        default="fiscal",
    )
    sequence = fields.Integer(default=10)
    version_display = fields.Char(string="Version Display")
    license_tier = fields.Selection(
        [("included", "Incluido"), ("std", "Standard"), ("pro", "Professional"), ("ent", "Enterprise")],
        default="ent",
    )
    active = fields.Boolean(default=True)
    line_ids = fields.One2many("justech.commercial.product.line", "product_id")
    module_map_ids = fields.One2many("justech.commercial.product.module", "product_id")

    _justech_commercial_product_code_uniq = models.Constraint(
        "UNIQUE(code)",
        "Commercial product code must be unique.",
    )


class JustechCommercialProductLine(models.Model):
    _name = "justech.commercial.product.line"
    _description = "Commercial Product Feature Line"
    _order = "sequence, commercial_name"

    product_id = fields.Many2one(
        "justech.commercial.product", required=True, ondelete="cascade", index=True
    )
    commercial_name = fields.Char(required=True)
    description = fields.Char()
    feature_code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    icon = fields.Char(default="fa-check-circle")


class JustechCommercialProductModule(models.Model):
    _name = "justech.commercial.product.module"
    _description = "Commercial Product Technical Module Mapping"

    product_id = fields.Many2one(
        "justech.commercial.product", required=True, ondelete="cascade", index=True
    )
    technical_module_code = fields.Char(required=True, index=True)
