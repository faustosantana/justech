import base64
import csv
import io
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class JustechDoFiscalReport(models.Model):
    _name = "justech.do.fiscal.report"
    _description = "Ejecución de reporte fiscal DGII"
    _order = "date_from desc, id desc"

    name = fields.Char(string="Nombre", required=True)
    report_type = fields.Selection(
        selection=[
            ("606", "606 — Compras"),
            ("607", "607 — Ventas"),
            ("608", "608 — NCF anulados"),
        ],
        string="Tipo de reporte",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(string="Desde", required=True)
    date_to = fields.Date(string="Hasta", required=True)
    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("done", "Generado"),
        ],
        string="Estado",
        default="draft",
    )
    generated_at = fields.Datetime(string="Fecha de generación", readonly=True)
    generated_by_id = fields.Many2one("res.users", string="Generado por", readonly=True)
    line_ids = fields.One2many(
        "justech.do.fiscal.report.line",
        "report_id",
        string="Líneas",
    )
    line_count = fields.Integer(string="Cantidad de líneas", compute="_compute_totals")
    total_untaxed = fields.Float(
        string="Subtotal gravado",
        compute="_compute_totals",
        digits=(16, 2),
    )
    total_tax = fields.Float(string="Total ITBIS", compute="_compute_totals", digits=(16, 2))
    total_amount = fields.Float(string="Total general", compute="_compute_totals", digits=(16, 2))
    export_file = fields.Binary(string="Archivo exportado", attachment=True)
    export_filename = fields.Char(string="Nombre de archivo")
    validation_log = fields.Text(string="Resultado de validación", readonly=True)
    validation_state = fields.Selection(
        selection=[
            ("pending", "Sin validar"),
            ("ok", "Válido"),
            ("error", "Con errores"),
        ],
        string="Estado validación",
        default="pending",
    )
    period_code = fields.Char(
        string="Período YYYYMM",
        compute="_compute_period_code",
        store=True,
    )

    @api.depends("date_from")
    def _compute_period_code(self):
        for rec in self:
            rec.period_code = rec.date_from.strftime("%Y%m") if rec.date_from else False

    @api.depends("line_ids", "line_ids.amount_untaxed", "line_ids.amount_tax", "line_ids.amount_total")
    def _compute_totals(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)
            rec.total_untaxed = sum(rec.line_ids.mapped("amount_untaxed"))
            rec.total_tax = sum(rec.line_ids.mapped("amount_tax"))
            rec.total_amount = sum(rec.line_ids.mapped("amount_total"))

    def _is_itbis_tax_line(self, line):
        tax = line.tax_line_id
        if not tax:
            return False
        name = (tax.name or "").upper()
        return "ITBIS" in name or (tax.amount in (18.0, 16.0, 9.0, 8.0) and tax.type_tax_use in ("sale", "purchase"))

    def _move_itbis_amount(self, move):
        return abs(
            sum(
                move.line_ids.filtered(self._is_itbis_tax_line).mapped("balance")
            )
        )

    def action_validate(self):
        for report in self:
            if report.report_type != "606":
                report.validation_log = _("Validación detallada solo disponible para formato 606.")
                report.validation_state = "ok"
                continue
            exporter = self.env["justech.do.dgii.606.exporter"]
            errors = exporter.validate_moves_606(
                report.company_id, report.date_from, report.date_to
            )
            if errors:
                report.validation_log = "\n".join(errors)
                report.validation_state = "error"
            else:
                report.validation_log = _("Sin errores. Listo para exportar el formato 606.")
                report.validation_state = "ok"
        return True

    def action_export_dgii_606(self):
        self.ensure_one()
        if self.report_type != "606":
            raise UserError(_("La exportación DGII oficial solo está disponible para el formato 606."))
        if self.state != "done":
            self.action_generate()
        exporter = self.env["justech.do.dgii.606.exporter"]
        content, filename = exporter.export_xlsx(
            self.company_id, self.date_from, self.date_to
        )
        self.write(
            {
                "export_file": content,
                "export_filename": filename,
                "validation_state": "ok",
                "validation_log": _("Archivo 606 generado correctamente."),
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": (
                f"/web/content/?model=justech.do.fiscal.report&id={self.id}"
                f"&field=export_file&filename_field=export_filename&download=true"
            ),
            "target": "self",
        }

    def action_generate(self):
        for report in self:
            report.line_ids.unlink()
            lines = report._collect_lines()
            report.write(
                {
                    "line_ids": [(0, 0, line) for line in lines],
                    "state": "done",
                    "generated_at": fields.Datetime.now(),
                    "generated_by_id": self.env.user.id,
                }
            )
        return True

    def _collect_lines(self):
        self.ensure_one()
        if self.report_type == "606":
            return self._lines_606()
        if self.report_type == "607":
            return self._lines_607()
        if self.report_type == "608":
            return self._lines_608()
        return []

    def _base_move_domain(self):
        return [
            ("company_id", "=", self.company_id.id),
            ("state", "=", "posted"),
            ("invoice_date", ">=", self.date_from),
            ("invoice_date", "<=", self.date_to),
        ]

    def _lines_606(self):
        moves = self.env["account.move"].search(
            self._base_move_domain()
            + [("move_type", "in", ("in_invoice", "in_refund"))]
        )
        lines = []
        for move in moves:
            itbis = self._move_itbis_amount(move)
            lines.append(
                {
                    "partner_vat": move.partner_id.vat or "",
                    "partner_name": move.partner_id.name,
                    "ncf": move.justech_do_ncf or move.ref or "",
                    "document_date": move.invoice_date,
                    "amount_untaxed": abs(move.amount_untaxed_signed),
                    "amount_tax": itbis,
                    "amount_total": abs(move.amount_total_signed),
                    "move_id": move.id,
                }
            )
        return lines

    def _lines_607(self):
        moves = self.env["account.move"].search(
            self._base_move_domain()
            + [
                ("move_type", "in", ("out_invoice", "out_refund")),
                ("justech_do_ncf_voided", "=", False),
            ]
        )
        lines = []
        for move in moves:
            if not move.justech_do_ncf:
                continue
            itbis = self._move_itbis_amount(move)
            lines.append(
                {
                    "partner_vat": move.partner_id.vat or "",
                    "partner_name": move.partner_id.name,
                    "ncf": move.justech_do_ncf,
                    "document_type": move.justech_do_document_type_id.prefix or "",
                    "document_date": move.invoice_date,
                    "amount_untaxed": abs(move.amount_untaxed_signed),
                    "amount_tax": itbis,
                    "amount_total": abs(move.amount_total_signed),
                    "move_id": move.id,
                }
            )
        return lines

    def _lines_608(self):
        moves = self.env["account.move"].search(
            self._base_move_domain() + [("justech_do_ncf_voided", "=", True)]
        )
        lines = []
        for move in moves.filtered("justech_do_ncf"):
            lines.append(
                {
                    "partner_vat": move.partner_id.vat or "",
                    "partner_name": move.partner_id.name,
                    "ncf": move.justech_do_ncf,
                    "document_date": move.justech_do_ncf_void_date or move.invoice_date,
                    "notes": move.justech_do_ncf_void_reason or "",
                    "move_id": move.id,
                }
            )
        return lines

    def action_export_csv(self):
        self.ensure_one()
        output = io.StringIO()
        if self.report_type == "606":
            fields_list = [
                "partner_vat",
                "partner_name",
                "ncf",
                "document_date",
                "amount_untaxed",
                "amount_tax",
                "amount_total",
            ]
            headers = {
                "partner_vat": "RNC",
                "partner_name": "Proveedor",
                "ncf": "NCF",
                "document_date": "Fecha",
                "amount_untaxed": "Monto gravado",
                "amount_tax": "ITBIS",
                "amount_total": "Total",
            }
        elif self.report_type == "607":
            fields_list = [
                "partner_vat",
                "partner_name",
                "ncf",
                "document_type",
                "document_date",
                "amount_untaxed",
                "amount_tax",
                "amount_total",
            ]
            headers = {
                "partner_vat": "RNC",
                "partner_name": "Cliente",
                "ncf": "NCF",
                "document_type": "Tipo",
                "document_date": "Fecha",
                "amount_untaxed": "Monto gravado",
                "amount_tax": "ITBIS",
                "amount_total": "Total",
            }
        else:
            fields_list = [
                "ncf",
                "partner_vat",
                "partner_name",
                "document_date",
                "notes",
            ]
            headers = {
                "ncf": "NCF",
                "partner_vat": "RNC",
                "partner_name": "Contacto",
                "document_date": "Fecha anulación",
                "notes": "Motivo",
            }
        writer = csv.DictWriter(
            output,
            fieldnames=[headers[f] for f in fields_list],
            extrasaction="ignore",
        )
        writer.writeheader()
        for line in self.line_ids:
            row = {}
            for field_name in fields_list:
                val = line[field_name]
                if isinstance(val, date):
                    val = val.isoformat()
                row[headers[field_name]] = val or ""
            writer.writerow(row)
        content = output.getvalue().encode("utf-8")
        filename = f"DGII_{self.report_type}_{self.date_from}_{self.date_to}.csv"
        self.write(
            {
                "export_file": base64.b64encode(content),
                "export_filename": filename,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/?model=justech.do.fiscal.report&id={self.id}&field=export_file&filename_field=export_filename&download=true",
            "target": "self",
        }

    def action_export_xlsx(self):
        self.ensure_one()
        try:
            import xlsxwriter
        except ImportError:
            return self.action_export_csv()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet(self.report_type)
        title_fmt = workbook.add_format({"bold": True})
        if self.report_type == "607":
            headers = [
                "RNC",
                "Cliente",
                "NCF",
                "Tipo",
                "Fecha",
                "Monto gravado",
                "ITBIS",
                "Total",
            ]
            row_fields = [
                "partner_vat",
                "partner_name",
                "ncf",
                "document_type",
                "document_date",
                "amount_untaxed",
                "amount_tax",
                "amount_total",
            ]
        elif self.report_type == "606":
            headers = ["RNC", "Proveedor", "NCF", "Fecha", "Monto gravado", "ITBIS", "Total"]
            row_fields = [
                "partner_vat",
                "partner_name",
                "ncf",
                "document_date",
                "amount_untaxed",
                "amount_tax",
                "amount_total",
            ]
        else:
            headers = ["NCF", "RNC", "Contacto", "Fecha anulación", "Motivo"]
            row_fields = [
                "ncf",
                "partner_vat",
                "partner_name",
                "document_date",
                "notes",
            ]
        meta = [
            (_("Compañía"), self.company_id.name),
            (_("Período"), f"{self.date_from} — {self.date_to}"),
            (_("Generado"), self.generated_at and self.generated_at.strftime("%Y-%m-%d %H:%M") or ""),
            (_("Usuario"), self.generated_by_id.name or ""),
            (_("Líneas"), self.line_count),
            (_("Subtotal gravado"), self.total_untaxed),
            (_("Total ITBIS"), self.total_tax),
            (_("Total general"), self.total_amount),
        ]
        row = 0
        for label, value in meta:
            sheet.write(row, 0, label, title_fmt)
            sheet.write(row, 1, value)
            row += 1
        row += 1
        for col, header in enumerate(headers):
            sheet.write(row, col, header, title_fmt)
        for row_idx, line in enumerate(self.line_ids, start=row + 1):
            for col_idx, field_name in enumerate(row_fields):
                val = line[field_name]
                if isinstance(val, date):
                    val = val.isoformat()
                sheet.write(row_idx, col_idx, val or "")
        workbook.close()
        content = output.getvalue()
        filename = f"DGII_{self.report_type}_{self.date_from}_{self.date_to}.xlsx"
        self.write(
            {
                "export_file": base64.b64encode(content),
                "export_filename": filename,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/?model=justech.do.fiscal.report&id={self.id}&field=export_file&filename_field=export_filename&download=true",
            "target": "self",
        }


class JustechDoFiscalReportLine(models.Model):
    _name = "justech.do.fiscal.report.line"
    _description = "Línea de reporte fiscal DGII"

    report_id = fields.Many2one(
        "justech.do.fiscal.report",
        string="Reporte",
        required=True,
        ondelete="cascade",
    )
    partner_vat = fields.Char(string="RNC")
    partner_name = fields.Char(string="Nombre")
    ncf = fields.Char(string="NCF")
    document_type = fields.Char(string="Tipo documento")
    document_date = fields.Date(string="Fecha")
    amount_untaxed = fields.Float(string="Monto gravado", digits=(16, 2))
    amount_tax = fields.Float(string="ITBIS", digits=(16, 2))
    amount_total = fields.Float(string="Total", digits=(16, 2))
    notes = fields.Text(string="Notas")
    move_id = fields.Many2one("account.move", string="Asiento")
