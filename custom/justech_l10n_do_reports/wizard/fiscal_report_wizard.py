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
    period_code = fields.Char(
        string="Período (YYYYMM)",
        required=True,
        default=lambda self: self.env["justech.do.dgii.period"].default_period_code(),
    )
    date_from = fields.Date(string="Desde", required=True)
    date_to = fields.Date(string="Hasta", required=True)
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
        string="Estado de validación",
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
    saved_report_id = fields.Many2one(
        "justech.do.fiscal.report",
        string="Revisión guardada",
        readonly=True,
    )
    date_from_display = fields.Char(
        string="Desde",
        compute="_compute_period_display",
    )
    date_to_display = fields.Char(
        string="Hasta",
        compute="_compute_period_display",
    )

    @api.depends("date_from", "date_to")
    def _compute_period_display(self):
        for wiz in self:
            wiz.date_from_display = (
                wiz.date_from.strftime("%d/%m/%Y") if wiz.date_from else ""
            )
            wiz.date_to_display = (
                wiz.date_to.strftime("%d/%m/%Y") if wiz.date_to else ""
            )

    @api.model_create_multi
    def create(self, vals_list):
        period_util = self.env["justech.do.dgii.period"]
        for vals in vals_list:
            if vals.get("period_code"):
                date_from, date_to = period_util.period_bounds_from_code(
                    vals["period_code"]
                )
                vals["date_from"] = date_from
                vals["date_to"] = date_to
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if vals.get("period_code"):
            period_util = self.env["justech.do.dgii.period"]
            for wiz in self:
                date_from, date_to = period_util.period_bounds_from_code(
                    wiz.period_code
                )
                super(JustechDoFiscalReportWizard, wiz).write(
                    {"date_from": date_from, "date_to": date_to}
                )
        return res

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        period_util = self.env["justech.do.dgii.period"]
        period_code = res.get("period_code") or period_util.default_period_code()
        date_from, date_to = period_util.period_bounds_from_code(period_code)
        res.update(
            {
                "period_code": period_code,
                "date_from": date_from,
                "date_to": date_to,
            }
        )
        return res

    @api.onchange("period_code")
    def _onchange_period_code(self):
        if not self.period_code:
            return
        try:
            date_from, date_to = self.env[
                "justech.do.dgii.period"
            ].period_bounds_from_code(self.period_code)
            self.date_from = date_from
            self.date_to = date_to
            self.validation_state = "pending"
            self.validation_log = False
        except UserError as err:
            return {
                "warning": {
                    "title": _("Período inválido"),
                    "message": str(err),
                }
            }

    @api.onchange("date_from", "date_to")
    def _onchange_dates(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            return {
                "warning": {
                    "title": _("Fechas incoherentes"),
                    "message": _("La fecha desde no puede ser posterior a la fecha hasta."),
                }
            }
        if self.date_from and self.date_to and self.period_code:
            try:
                self.env["justech.do.dgii.period"].validate_period_dates(
                    self.date_from, self.date_to, self.period_code
                )
            except UserError as err:
                return {
                    "warning": {
                        "title": _("Período incoherente"),
                        "message": str(err),
                    }
                }

    def _check_period(self):
        self.ensure_one()
        period_util = self.env["justech.do.dgii.period"]
        period_util.period_bounds_from_code(self.period_code)
        period_util.validate_period_dates(
            self.date_from, self.date_to, self.period_code
        )

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
                "name": f"{label} {self.period_code} — revisión fiscal",
                "report_type": self.report_type,
                "period_code": self.period_code,
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
                "state": "draft",
            }
        )

    def _open_review_form(self, report):
        review_form = self.env.ref(
            "justech_l10n_do_reports.view_justech_do_fiscal_report_review_form",
            raise_if_not_found=False,
        )
        views = [(review_form.id, "form")] if review_form else []
        return {
            "type": "ir.actions.act_window",
            "name": _("Revisión fiscal DGII"),
            "res_model": "justech.do.fiscal.report",
            "res_id": report.id,
            "view_mode": "form",
            "views": views or False,
            "target": "current",
        }

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

    def action_save_review(self):
        """Crea un registro persistente de revisión fiscal con todas las líneas."""
        self.ensure_one()
        self._check_period()
        if self.report_type == "606" and self.validation_state == "pending":
            self.action_validate()
        report = self._create_report()
        report.action_load_review_lines()
        if self.report_type == "606":
            report.action_validate_period()
        else:
            report._transition_state("validated", _("Revisión guardada."))
        self.saved_report_id = report.id
        return self._open_review_form(report)

    def action_view_documents(self):
        """Abre la revisión guardada o la crea si aún no existe."""
        self.ensure_one()
        if self.saved_report_id:
            return self._open_review_form(self.saved_report_id)
        return self.action_save_review()

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
            if self.validation_state == "pending":
                self.action_validate()
            report = self._create_report()
            report.action_load_review_lines()
            report.action_validate_period()
            if report.manual_exclusion_count and report.state != "approved":
                return report.action_open_export_blocker_wizard()
            result = report.action_generate_dgii_export()
            if isinstance(result, dict):
                return result
            return result
        report = self._create_report()
        report.action_generate()
        return self._open_review_form(report)

    def action_generate_history(self):
        """Alias retrocompatible — guarda revisión fiscal persistente."""
        return self.action_save_review()
