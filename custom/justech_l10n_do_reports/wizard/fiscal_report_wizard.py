from odoo import fields, models


class JustechDoFiscalReportWizard(models.TransientModel):
    _name = "justech.do.fiscal.report.wizard"
    _description = "Asistente para generar reporte fiscal DGII"

    report_type = fields.Selection(
        selection=[
            ("606", "606 — Compras"),
            ("607", "607 — Ventas"),
            ("608", "608 — NCF anulados"),
        ],
        string="Tipo de reporte",
        required=True,
        default="607",
    )
    date_from = fields.Date(string="Desde", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="Hasta", required=True, default=fields.Date.context_today)
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )

    def action_generate(self):
        self.ensure_one()
        labels = dict(self._fields["report_type"].selection)
        label = labels.get(self.report_type, self.report_type)
        report = self.env["justech.do.fiscal.report"].create(
            {
                "name": f"{label} {self.date_from} — {self.date_to}",
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
