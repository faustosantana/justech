from odoo import api, fields, models


class JustechDgcpOpportunityLine(models.Model):
    _name = "justech.dgcp.opportunity.line"
    _description = "Producto solicitado DGCP"
    _order = "line_number, id"

    lead_id = fields.Many2one(
        "crm.lead",
        string="Oportunidad",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        related="lead_id.company_id",
        store=True,
        readonly=True,
    )
    dgcp_process_code = fields.Char(string="Código DGCP", index=True)
    dgcp_process_id = fields.Char(string="ID proceso JAIOS", index=True)
    dgcp_line_id = fields.Char(string="ID línea DGCP/JAIOS", index=True)
    line_number = fields.Integer(string="#", default=1, index=True)

    description_original = fields.Text(string="Descripción original", required=True)
    quantity = fields.Float(string="Cantidad", default=1.0)
    uom_text = fields.Char(string="Unidad")
    specifications = fields.Text(string="Especificaciones")
    brand_required = fields.Char(string="Marca requerida")
    model_required = fields.Char(string="Modelo requerido")
    reference = fields.Char(string="Referencia")
    estimated_unit_price = fields.Float(string="Precio estimado")
    estimated_total = fields.Float(
        string="Total estimado",
        compute="_compute_estimated_total",
        store=True,
    )
    currency_id = fields.Many2one("res.currency", string="Moneda")

    product_id = fields.Many2one("product.product", string="Producto Odoo")
    product_template_id = fields.Many2one(
        "product.template",
        string="Plantilla producto",
        related="product_id.product_tmpl_id",
        store=True,
        readonly=True,
    )
    match_state = fields.Selection(
        [
            ("unlinked", "Sin vincular"),
            ("suggested", "Sugerido"),
            ("linked", "Vinculado"),
            ("review_required", "Requiere revisión"),
        ],
        string="Estado vínculo",
        default="unlinked",
        required=True,
        index=True,
    )
    match_confidence = fields.Float(string="Confianza match")
    match_method = fields.Char(string="Método match")
    match_approved = fields.Boolean(string="Match aprobado", default=False)
    match_approved_by_jaios_id = fields.Char(string="Aprobó match (ID JAIOS)")
    match_approved_by_name = fields.Char(string="Aprobó match (nombre)")

    jaios_created_by_id = fields.Char(string="Creado por JAIOS (ID)")
    jaios_created_by_name = fields.Char(string="Creado por JAIOS")
    jaios_updated_by_id = fields.Char(string="Actualizado por JAIOS (ID)")
    jaios_updated_by_name = fields.Char(string="Actualizado por JAIOS")
    last_sync_at = fields.Datetime(string="Última sync")

    document_ref = fields.Char(string="Ref. documento/sección")

    @api.depends("quantity", "estimated_unit_price")
    def _compute_estimated_total(self):
        for line in self:
            line.estimated_total = (line.quantity or 0.0) * (line.estimated_unit_price or 0.0)

    def action_use_suggested_product(self):
        """Confirma el producto sugerido como vinculado (sin crear catálogo)."""
        for line in self:
            if not line.product_id:
                continue
            line.write(
                {
                    "match_state": "linked",
                    "match_approved": True,
                }
            )
        return True

    def action_clear_product_link(self):
        for line in self:
            line.write(
                {
                    "product_id": False,
                    "match_state": "unlinked",
                    "match_confidence": 0.0,
                    "match_method": False,
                    "match_approved": False,
                    "match_approved_by_jaios_id": False,
                    "match_approved_by_name": False,
                }
            )
        return True
