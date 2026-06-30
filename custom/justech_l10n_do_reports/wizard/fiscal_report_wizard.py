from odoo import fields, models


class JustechDoFiscalReportWizard(models.TransientModel):
    _name = "justech.do.fiscal.report.wizard"
    _description = "Generate DGII Fiscal Report"

    report_type = fields.Selection(
        selection=[
            ("606", "606 — Purchases"),
            ("607", "607 — Sales"),
            ("608", "608 — Voided NCF"),
        ],
        required=True,
        default="607",
    )
    date_from = fields.Date(required=True, default=fields.Date.context_today)
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )

    def action_generate(self):
        self.ensure_one()
        report = self.env["justech.do.fiscal.report"].create(
            {
                "name": f"{self.report_type} {self.date_from} — {self.date_to}",
                "report_type": self.report_type,
                "date_from": self.date_from,
                "date_to": self.date_to,
                "company_id": self.company_id.id,
            }
        )
        report.action_generate()
        return {
            "type": "ir.actions.act_window",
            "res_model": "justech.do.fiscal.report",
            "res_id": report.id,
            "view_mode": "form",
            "target": "current",
        }
