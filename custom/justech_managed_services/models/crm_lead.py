# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    justech_ms_assessment_count = fields.Integer(
        string="Levantamientos",
        compute="_compute_justech_ms_assessment_count",
    )

    def _compute_justech_ms_assessment_count(self):
        Assessment = self.env["justech.managed.service.assessment"]
        if not Assessment.has_access("read"):
            for lead in self:
                lead.justech_ms_assessment_count = 0
            return
        grouped = Assessment.read_group(
            [("opportunity_id", "in", self.ids)],
            ["opportunity_id"],
            ["opportunity_id"],
        )
        counts = {
            row["opportunity_id"][0]: row["opportunity_id_count"]
            for row in grouped
        }
        for lead in self:
            lead.justech_ms_assessment_count = counts.get(lead.id, 0)

    def action_view_justech_ms_assessments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Levantamientos",
            "res_model": "justech.managed.service.assessment",
            "view_mode": "list,form",
            "domain": [("opportunity_id", "=", self.id)],
            "context": {"default_opportunity_id": self.id},
        }
