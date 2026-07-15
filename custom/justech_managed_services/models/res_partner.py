# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    justech_ms_assessment_count = fields.Integer(
        string="Levantamientos",
        compute="_compute_justech_ms_assessment_count",
    )

    def _compute_justech_ms_assessment_count(self):
        Assessment = self.env["justech.managed.service.assessment"]
        if not Assessment.has_access("read"):
            for partner in self:
                partner.justech_ms_assessment_count = 0
            return
        grouped = Assessment.read_group(
            [("partner_id", "in", self.ids)],
            ["partner_id"],
            ["partner_id"],
        )
        counts = {
            row["partner_id"][0]: row["partner_id_count"] for row in grouped
        }
        for partner in self:
            partner.justech_ms_assessment_count = counts.get(partner.id, 0)

    def action_view_justech_ms_assessments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Levantamientos",
            "res_model": "justech.managed.service.assessment",
            "view_mode": "list,form",
            "domain": [("partner_id", "=", self.id)],
            "context": {"default_partner_id": self.id},
        }
