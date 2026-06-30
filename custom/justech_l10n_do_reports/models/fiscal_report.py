import base64
import csv
import io
from datetime import date

from odoo import _, api, fields, models


class JustechDoFiscalReport(models.Model):
    _name = "justech.do.fiscal.report"
    _description = "Dominican DGII Fiscal Report Run"
    _order = "date_from desc, id desc"

    name = fields.Char(required=True)
    report_type = fields.Selection(
        selection=[
            ("606", "606 — Purchases"),
            ("607", "607 — Sales"),
            ("608", "608 — Voided NCF"),
        ],
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("done", "Done"),
        ],
        default="draft",
    )
    line_ids = fields.One2many(
        "justech.do.fiscal.report.line",
        "report_id",
        string="Lines",
    )
    line_count = fields.Integer(compute="_compute_line_count")
    export_file = fields.Binary(attachment=True)
    export_filename = fields.Char()

    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def action_generate(self):
        for report in self:
            report.line_ids.unlink()
            lines = report._collect_lines()
            report.write(
                {
                    "line_ids": [(0, 0, line) for line in lines],
                    "state": "done",
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
            itbis = sum(
                move.line_ids.filtered(
                    lambda l: l.tax_line_id and "ITBIS" in (l.tax_line_id.name or "").upper()
                ).mapped("balance")
            )
            lines.append(
                {
                    "partner_vat": move.partner_id.vat or "",
                    "partner_name": move.partner_id.name,
                    "ncf": move.justech_do_ncf or move.ref or "",
                    "document_date": move.invoice_date,
                    "amount_untaxed": abs(move.amount_untaxed_signed),
                    "amount_tax": abs(itbis),
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
            itbis = sum(
                move.line_ids.filtered(
                    lambda l: l.tax_line_id and "ITBIS" in (l.tax_line_id.name or "").upper()
                ).mapped("balance")
            )
            lines.append(
                {
                    "partner_vat": move.partner_id.vat or "",
                    "partner_name": move.partner_id.name,
                    "ncf": move.justech_do_ncf,
                    "document_type": move.justech_do_document_type_id.prefix or "",
                    "document_date": move.invoice_date,
                    "amount_untaxed": abs(move.amount_untaxed_signed),
                    "amount_tax": abs(itbis),
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
        else:
            fields_list = [
                "ncf",
                "partner_vat",
                "partner_name",
                "document_date",
                "notes",
            ]
        writer = csv.DictWriter(output, fieldnames=fields_list, extrasaction="ignore")
        writer.writeheader()
        for line in self.line_ids:
            writer.writerow({f: line[f] for f in fields_list if f in line._fields})
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
        if self.report_type == "607":
            headers = [
                "RNC",
                "Customer",
                "NCF",
                "Type",
                "Date",
                "Untaxed",
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
            headers = ["RNC", "Vendor", "NCF", "Date", "Untaxed", "ITBIS", "Total"]
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
            headers = ["NCF", "RNC", "Partner", "Void Date", "Reason"]
            row_fields = [
                "ncf",
                "partner_vat",
                "partner_name",
                "document_date",
                "notes",
            ]
        for col, header in enumerate(headers):
            sheet.write(0, col, header)
        for row_idx, line in enumerate(self.line_ids, start=1):
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
    _description = "Dominican DGII Fiscal Report Line"

    report_id = fields.Many2one(
        "justech.do.fiscal.report",
        required=True,
        ondelete="cascade",
    )
    partner_vat = fields.Char(string="RNC")
    partner_name = fields.Char()
    ncf = fields.Char()
    document_type = fields.Char()
    document_date = fields.Date()
    amount_untaxed = fields.Float(digits=(16, 2))
    amount_tax = fields.Float(digits=(16, 2))
    amount_total = fields.Float(digits=(16, 2))
    notes = fields.Text()
    move_id = fields.Many2one("account.move")
