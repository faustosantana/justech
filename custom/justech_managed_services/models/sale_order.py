# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    justech_managed_service_id = fields.Many2one(
        "justech.managed.service",
        string="Servicio Administrado",
        index=True,
        copy=False,
    )
    justech_assessment_id = fields.Many2one(
        "justech.managed.service.assessment",
        string="Levantamiento",
        index=True,
        copy=False,
    )

    def action_view_justech_managed_service(self):
        self.ensure_one()
        if not self.justech_managed_service_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "justech.managed.service",
            "res_id": self.justech_managed_service_id.id,
            "view_mode": "form",
            "target": "current",
        }
