# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    justech_managed_service_id = fields.Many2one(
        "justech.managed.service",
        string="Servicio Administrado",
        index=True,
        copy=False,
        domain="[('partner_id', 'child_of', partner_id)]",
    )

    @api.onchange("partner_id")
    def _onchange_partner_justech_ms(self):
        if self.partner_id and self.justech_managed_service_id:
            commercial = self.partner_id.commercial_partner_id
            if self.justech_managed_service_id.partner_id != commercial:
                self.justech_managed_service_id = False
        if self.partner_id and not self.justech_managed_service_id:
            service = self.env["justech.managed.service"].search(
                [
                    ("partner_id", "=", self.partner_id.commercial_partner_id.id),
                    ("state", "=", "active"),
                ],
                limit=1,
            )
            if service:
                self.justech_managed_service_id = service
