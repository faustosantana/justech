from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    justech_dgcp_code = fields.Char(string="Código DGCP", index=True, copy=False)
    justech_jaios_id = fields.Char(string="ID JAIOS/DGCP", index=True, copy=False)
    justech_institution = fields.Char(string="Entidad contratante")
    justech_company_key = fields.Char(string="Empresa participante")
    justech_rpe = fields.Char(string="RPE")
    justech_amount = fields.Float(string="Monto estimado")
    justech_currency = fields.Char(string="Moneda", default="DOP")
    justech_publish_date = fields.Date(string="Fecha publicación")
    justech_deadline = fields.Date(string="Fecha límite DGCP")
    justech_url = fields.Char(string="URL DGCP")
    justech_dgcp_status = fields.Char(string="Estado DGCP")
    justech_jaios_stage = fields.Char(string="Etapa JAIOS")
    justech_awarded_amount = fields.Float(string="Monto adjudicado")
    justech_awarded_date = fields.Date(string="Fecha adjudicación")
    justech_result = fields.Char(string="Resultado")

    # Identidad JAIOS (NO confundir con create_uid de Odoo)
    justech_jaios_user_id = fields.Char(string="Iniciado por (ID JAIOS)", index=True, copy=False)
    justech_jaios_user_name = fields.Char(string="Iniciado por (nombre)")
    justech_jaios_user_email = fields.Char(string="Iniciado por (email)")
    justech_jaios_owner_id = fields.Char(string="Responsable JAIOS (ID)", index=True, copy=False)
    justech_jaios_owner_name = fields.Char(string="Responsable JAIOS (nombre)")
    justech_jaios_owner_email = fields.Char(string="Responsable JAIOS (email)")
    justech_jaios_last_sync_at = fields.Datetime(string="Última sync JAIOS")
    justech_jaios_url = fields.Char(string="URL JAIOS")
    justech_jaios_last_action_user_id = fields.Char(string="Última acción JAIOS (ID)")
    justech_jaios_last_action_user_name = fields.Char(string="Última acción JAIOS (nombre)")
    justech_jaios_last_action_at = fields.Datetime(string="Última acción JAIOS (fecha)")
    justech_jaios_odoo_user_id = fields.Integer(
        string="Usuario Odoo mapeado (informativo)",
        help="res.users id si el email JAIOS coincide de forma única. No asigna vendedor automáticamente.",
    )

    justech_sale_count = fields.Integer(compute="_compute_justech_counts")
    justech_purchase_count = fields.Integer(compute="_compute_justech_counts")
    justech_delivery_count = fields.Integer(compute="_compute_justech_counts")
    justech_invoice_count = fields.Integer(compute="_compute_justech_counts")

    @api.depends("justech_dgcp_code", "order_ids")
    def _compute_justech_counts(self):
        Sale = self.env["sale.order"]
        Purchase = self.env["purchase.order"]
        Picking = self.env["stock.picking"]
        for lead in self:
            code = lead.justech_dgcp_code
            orders = lead.order_ids
            if code:
                extra = Sale.search([("justech_dgcp_code", "=", code), ("id", "not in", orders.ids)])
                orders |= extra
            lead.justech_sale_count = len(orders)
            pos = Purchase.browse()
            pickings = Picking.browse()
            invoices = self.env["account.move"].browse()
            if orders:
                pos = Purchase.search([("origin", "in", orders.mapped("name"))])
                pickings = Picking.search([("sale_id", "in", orders.ids)])
                invoices = orders.mapped("invoice_ids")
            if code:
                pos |= Purchase.search([("origin", "ilike", code)])
            lead.justech_purchase_count = len(pos)
            lead.justech_delivery_count = len(pickings)
            lead.justech_invoice_count = len(invoices)

    def action_open_justech_dgcp(self):
        self.ensure_one()
        url = self.justech_url
        if not url:
            return False
        return {"type": "ir.actions.act_url", "url": url, "target": "new"}

    def action_open_justech_jaios(self):
        self.ensure_one()
        url = self.justech_jaios_url
        if not url:
            return False
        return {"type": "ir.actions.act_url", "url": url, "target": "new"}

    def action_open_justech_sales(self):
        self.ensure_one()
        domain = [("opportunity_id", "=", self.id)]
        if self.justech_dgcp_code:
            domain = ["|", ("opportunity_id", "=", self.id), ("justech_dgcp_code", "=", self.justech_dgcp_code)]
        return {
            "type": "ir.actions.act_window",
            "name": "Cotizaciones / Ventas",
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": domain,
        }

    def action_open_justech_purchases(self):
        self.ensure_one()
        orders = self.env["sale.order"].search(
            ["|", ("opportunity_id", "=", self.id), ("justech_dgcp_code", "=", self.justech_dgcp_code or "__none__")]
        )
        domain = [("origin", "in", orders.mapped("name"))]
        if self.justech_dgcp_code:
            domain = ["|", ("origin", "in", orders.mapped("name")), ("origin", "ilike", self.justech_dgcp_code)]
        return {
            "type": "ir.actions.act_window",
            "name": "Compras",
            "res_model": "purchase.order",
            "view_mode": "list,form",
            "domain": domain,
        }

    def action_open_justech_deliveries(self):
        self.ensure_one()
        orders = self.env["sale.order"].search(
            ["|", ("opportunity_id", "=", self.id), ("justech_dgcp_code", "=", self.justech_dgcp_code or "__none__")]
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Entregas",
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": [("sale_id", "in", orders.ids)],
        }

    def action_open_justech_invoices(self):
        self.ensure_one()
        orders = self.env["sale.order"].search(
            ["|", ("opportunity_id", "=", self.id), ("justech_dgcp_code", "=", self.justech_dgcp_code or "__none__")]
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Facturas",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", orders.mapped("invoice_ids").ids)],
        }
