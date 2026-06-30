from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
        default="606",
    )
    date_from = fields.Date(string="Desde", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="Hasta", required=True, default=fields.Date.context_today)
    period_code = fields.Char(
        string="Período (YYYYMM)",
        compute="_compute_period_code",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    validation_log = fields.Text(string="Resultado de validación", readonly=True)
    validation_state = fields.Selection(
        selection=[
            ("pending", "Sin validar"),
            ("ok", "Válido"),
            ("error", "Con errores"),
        ],
        default="pending",
        readonly=True,
    )

    @api.depends("date_from")
    def _compute_period_code(self):
        for wiz in self:
            wiz.period_code = wiz.date_from.strftime("%Y%m") if wiz.date_from else False

    def _check_period(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("La fecha desde no puede ser posterior a la fecha hasta."))

    def _create_report(self):
        self.ensure_one()
        self._check_period()
        labels = dict(self._fields["report_type"].selection)
        label = labels.get(self.report_type, self.report_type)
        return self.env["justech.do.fiscal.report"].create(
            {
                "name": f"{label} {self.period_code or self.date_from} — {self.date_to}",
                "report_type": self.report_type,
                "date_from": self.date_from,
                "date_to": self.date_to,
                "company_id": self.company_id.id,
                "validation_log": self.validation_log,
                "validation_state": self.validation_state,
            }
        )

    def action_validate(self):
        self.ensure_one()
        self._check_period()
        if self.report_type != "606":
            self.validation_log = _("Validación detallada solo disponible para formato 606.")
            self.validation_state = "ok"
        else:
            exporter = self.env["justech.do.dgii.606.exporter"]
            errors = exporter.validate_moves_606(
                self.company_id, self.date_from, self.date_to
            )
            if errors:
                self.validation_log = "\n".join(errors)
                self.validation_state = "error"
            else:
                self.validation_log = _("Sin errores. Listo para exportar el formato 606.")
                self.validation_state = "ok"
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_generate(self):
        self.ensure_one()
        if self.report_type == "606" and self.validation_state != "ok":
            self.action_validate()
            if self.validation_state == "error":
                raise UserError(
                    _("Corrija los errores de validación antes de generar el 606:\n\n%s")
                    % (self.validation_log or "")
                )
        report = self._create_report()
        report.action_generate()
        if self.report_type == "606":
            return report.action_export_dgii_606()
        return {
            "type": "ir.actions.act_window",
            "res_model": "justech.do.fiscal.report",
            "res_id": report.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_generate_history(self):
        """Genera historial sin descargar — útil para revisar líneas antes de exportar."""
        self.ensure_one()
        report = self._create_report()
        report.action_generate()
        return {
            "type": "ir.actions.act_window",
            "res_model": "justech.do.fiscal.report",
            "res_id": report.id,
            "view_mode": "form",
            "target": "current",
        }
