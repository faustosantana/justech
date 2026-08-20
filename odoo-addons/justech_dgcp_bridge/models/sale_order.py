from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    justech_dgcp_code = fields.Char(string="Licitación DGCP", index=True, copy=False)
    justech_jaios_id = fields.Char(string="ID JAIOS/DGCP", copy=False)
    justech_jaios_user_name = fields.Char(
        string="Iniciado en JAIOS por",
        related="opportunity_id.justech_jaios_user_name",
        readonly=True,
        store=False,
    )
    justech_jaios_owner_name = fields.Char(
        string="Responsable JAIOS",
        related="opportunity_id.justech_jaios_owner_name",
        readonly=True,
        store=False,
    )
    justech_jaios_url = fields.Char(
        string="URL JAIOS",
        related="opportunity_id.justech_jaios_url",
        readonly=True,
        store=False,
    )

    def action_open_justech_opportunity(self):
        self.ensure_one()
        if not self.opportunity_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": "Oportunidad CRM",
            "res_model": "crm.lead",
            "res_id": self.opportunity_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_justech_jaios(self):
        self.ensure_one()
        url = self.justech_jaios_url
        if not url and self.opportunity_id:
            url = self.opportunity_id.justech_jaios_url
        if not url:
            return False
        return {"type": "ir.actions.act_url", "url": url, "target": "new"}
