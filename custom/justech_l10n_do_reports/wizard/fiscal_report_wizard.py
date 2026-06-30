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
            ("warning", "Con advertencias"),
            ("error", "Sin documentos válidos"),
        ],
        default="pending",
        readonly=True,
    )
    count_all = fields.Integer(string="Documentos en período", readonly=True)
    count_valid = fields.Integer(string="Válidos para exportar", readonly=True)
    count_incomplete = fields.Integer(string="Incompletos", readonly=True)
    count_excluded = fields.Integer(string="Excluidos", readonly=True)
    count_cancelled = fields.Integer(string="Anulados", readonly=True)
    count_partners_errors = fields.Integer(string="Proveedores con errores", readonly=True)
    error_report_file = fields.Binary(string="Reporte de errores", readonly=True)
    error_report_filename = fields.Char(string="Nombre reporte errores", readonly=True)

    @api.depends("date_from")
    def _compute_period_code(self):
        for wiz in self:
            wiz.period_code = wiz.date_from.strftime("%Y%m") if wiz.date_from else False

    def _check_period(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("La fecha desde no puede ser posterior a la fecha hasta."))

    def _apply_validation_result(self, result):
        self.ensure_one()
        counts = result["counts"]
        self.count_all = counts["all"]
        self.count_valid = counts["valid"]
        self.count_incomplete = counts["incomplete"]
        self.count_excluded = counts["excluded"]
        self.count_cancelled = counts["cancelled"]
        self.count_partners_errors = counts["partners_affected"]
        self.validation_log = self.env["justech.do.dgii.606.exporter"].format_validation_summary(
            result
        )
        error_content, error_filename = self.env[
            "justech.do.dgii.606.exporter"
        ].export_errors_xlsx(
            self.company_id, self.date_from, self.date_to, result=result
        )
        self.error_report_file = error_content
        self.error_report_filename = error_filename
        if counts["valid"] and counts["incomplete"]:
            self.validation_state = "warning"
        elif counts["valid"]:
            self.validation_state = "ok"
        else:
            self.validation_state = "error"

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
                "count_all": self.count_all,
                "count_valid": self.count_valid,
                "count_incomplete": self.count_incomplete,
                "count_excluded": self.count_excluded,
                "count_cancelled": self.count_cancelled,
                "count_partners_errors": self.count_partners_errors,
                "error_report_file": self.error_report_file,
                "error_report_filename": self.error_report_filename,
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
            result = exporter.validate_period_606(
                self.company_id, self.date_from, self.date_to
            )
            self._apply_validation_result(result)
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_download_errors(self):
        self.ensure_one()
        if not self.error_report_file:
            if self.report_type == "606":
                self.action_validate()
            if not self.error_report_file:
                raise UserError(_("No hay reporte de errores para descargar."))
        return {
            "type": "ir.actions.act_url",
            "url": (
                f"/web/content/?model={self._name}&id={self.id}"
                f"&field=error_report_file&filename_field=error_report_filename&download=true"
            ),
            "target": "self",
        }

    def action_generate(self):
        self.ensure_one()
        if self.report_type == "606":
            exporter = self.env["justech.do.dgii.606.exporter"]
            if self.validation_state == "pending":
                self.action_validate()
            result = exporter.validate_period_606(
                self.company_id, self.date_from, self.date_to
            )
            valid_moves = result["buckets"]["valid"]
            if not valid_moves:
                raise UserError(
                    self.validation_log
                    or _("No hay documentos fiscalmente válidos para exportar.")
                )
            report = self._create_report()
            report.action_generate(valid_moves=valid_moves)
            return report.action_export_dgii_606(moves=valid_moves)
        report = self._create_report()
        report.action_generate()
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
        if self.report_type == "606" and self.validation_state == "pending":
            self.action_validate()
        report = self._create_report()
        if self.report_type == "606":
            exporter = self.env["justech.do.dgii.606.exporter"]
            result = exporter.validate_period_606(
                self.company_id, self.date_from, self.date_to
            )
            report.action_generate(valid_moves=result["buckets"]["valid"])
        else:
            report.action_generate()
        return {
            "type": "ir.actions.act_window",
            "res_model": "justech.do.fiscal.report",
            "res_id": report.id,
            "view_mode": "form",
            "target": "current",
        }
