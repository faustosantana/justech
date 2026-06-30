"""Exportador piloto DGII 606 — layout oficial según dgii_606_mapping.json."""
from __future__ import annotations

import base64
import io
import json
import re
from datetime import date
from pathlib import Path

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round


class JustechDoDgii606Exporter(models.AbstractModel):
    _name = "justech.do.dgii.606.exporter"
    _description = "Exportador DGII formato 606"

    @classmethod
    def _mapping_path(cls):
        return Path(__file__).resolve().parent.parent / "data" / "dgii_606_mapping.json"

    def _load_mapping(self):
        path = self._mapping_path()
        if not path.is_file():
            raise UserError(_("No se encontró el mapeo DGII 606 en %s") % path)
        return json.loads(path.read_text(encoding="utf-8"))

    def _format_dgii_date(self, value):
        if not value:
            return ""
        if isinstance(value, str):
            return value.replace("-", "")
        return fields.Date.to_date(value).strftime("%Y%m%d")

    def _format_amount(self, amount, digits=2):
        return float_round(abs(amount or 0.0), precision_digits=digits)

    def _is_itbis_tax(self, tax):
        if not tax:
            return False
        name = (tax.name or "").upper()
        return "ITBIS" in name or (
            tax.amount in (18.0, 16.0, 9.0, 8.0) and tax.type_tax_use == "purchase"
        )

    def _is_withholding_tax_line(self, line):
        tax = line.tax_line_id
        return bool(tax and tax.amount < 0)

    def _catalog_for_tax(self, tax, company):
        if not tax:
            return self.env["hellenia.withholding.catalog"]
        return self.env["hellenia.withholding.catalog"].search(
            [("tax_id", "=", tax.id), ("company_id", "=", company.id)],
            limit=1,
        )

    def _withholding_breakdown(self, move):
        """ITBIS retenido, ISR retenido y tipo ISR para 606."""
        itbis_wh = 0.0
        isr_wh = 0.0
        isr_type = ""
        missing_codes = []
        Catalog = self.env["hellenia.withholding.catalog"]
        if Catalog._name not in self.env:
            return itbis_wh, isr_wh, isr_type, missing_codes
        for line in move.line_ids.filtered(self._is_withholding_tax_line):
            tax = line.tax_line_id
            catalog = self._catalog_for_tax(tax, move.company_id)
            amount = self._format_amount(line.balance)
            if catalog.withholding_type == "itbis":
                itbis_wh += amount
            elif catalog.withholding_type == "isr":
                isr_wh += amount
                if catalog.dgii_withholding_code:
                    isr_type = catalog.dgii_withholding_code
                elif catalog.affects_606:
                    missing_codes.append(catalog.display_name)
            elif tax and catalog:
                missing_codes.append(catalog.display_name or tax.name)
        return itbis_wh, isr_wh, isr_type, missing_codes

    def _split_goods_services(self, move):
        goods = 0.0
        services = 0.0
        for line in move.invoice_line_ids.filtered(lambda l: not l.display_type):
            base = abs(line.price_subtotal)
            product = line.product_id
            if product and product.type == "service":
                services += base
            else:
                goods += base
        if not goods and not services:
            goods = abs(move.amount_untaxed_signed)
        return services, goods

    def _payment_date(self, move, date_from, date_to):
        payments = move._get_reconciled_payments()
        dates = []
        for payment in payments:
            pay_date = payment.date
            if pay_date and date_from <= pay_date <= date_to:
                dates.append(pay_date)
        return min(dates) if dates else False

    def _payment_method_code(self, move):
        if move.move_type == "in_refund":
            return "06"
        if move.payment_state in ("paid", "in_payment"):
            payments = move._get_reconciled_payments()
            if payments:
                name = (payments[0].payment_method_line_id.name or "").lower()
                if "efectivo" in name or "cash" in name:
                    return "01"
                if "tarjeta" in name or "card" in name:
                    return "03"
                if "cheque" in name:
                    return "02"
                return "02"
            return "02"
        if move.payment_state == "not_paid":
            return "04"
        return "07"

    def _expense_type_code(self, move):
        """P1 pendiente — valor por defecto normativo para piloto."""
        doc = move.justech_do_document_type_id
        if doc and doc.prefix == "B13":
            return "06"
        return "02"

    def _moves_for_period(self, company, date_from, date_to):
        return self.env["account.move"].search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "posted"),
                ("move_type", "in", ("in_invoice", "in_refund")),
                ("invoice_date", ">=", date_from),
                ("invoice_date", "<=", date_to),
                ("justech_do_dgii_line_status", "=", "1"),
            ],
            order="invoice_date, id",
        )

    def validate_moves_606(self, company, date_from, date_to, moves=None):
        moves = moves or self._moves_for_period(company, date_from, date_to)
        errors = []
        for move in moves:
            label = move.name or move.ref or str(move.id)
            partner = move.partner_id
            if not partner.vat:
                errors.append(
                    _("%(doc)s: el proveedor %(partner)s no tiene RNC/Cédula.")
                    % {"doc": label, "partner": partner.display_name}
                )
            if not partner.justech_do_partner_id_type:
                errors.append(
                    _("%(doc)s: el proveedor %(partner)s no tiene tipo de identificación DGII.")
                    % {"doc": label, "partner": partner.display_name}
                )
            if not move.justech_do_ncf:
                errors.append(_("%(doc)s: la factura no tiene NCF.") % {"doc": label})
            if move.invoice_date and (move.invoice_date < date_from or move.invoice_date > date_to):
                errors.append(
                    _("%(doc)s: la fecha %(fecha)s está fuera del período.")
                    % {"doc": label, "fecha": move.invoice_date}
                )
            positive_taxes = move.line_ids.filtered(
                lambda l: l.tax_line_id and l.tax_line_id.amount > 0
            )
            unknown = positive_taxes.filtered(
                lambda l: not self._is_itbis_tax(l.tax_line_id)
                and "ISC" not in (l.tax_line_id.name or "").upper()
                and l.tax_line_id.type_tax_use == "purchase"
            )
            if unknown:
                errors.append(
                    _("%(doc)s: impuesto no clasificado para DGII: %(taxes)s")
                    % {
                        "doc": label,
                        "taxes": ", ".join(unknown.mapped("tax_line_id.name")),
                    }
                )
            _, _, _, missing_codes = self._withholding_breakdown(move)
            for wh_name in missing_codes:
                errors.append(
                    _("%(doc)s: retención «%(wh)s» sin código DGII configurado.")
                    % {"doc": label, "wh": wh_name}
                )
        return errors

    def build_row_values(self, move, line_number, date_from, date_to):
        partner = move.partner_id
        services, goods = self._split_goods_services(move)
        itbis = self._format_amount(self.env["justech.do.fiscal.report"]._move_itbis_amount(move))
        itbis_wh, isr_wh, isr_type, _missing = self._withholding_breakdown(move)
        total_untaxed = self._format_amount(move.amount_untaxed_signed)
        pay_date = self._payment_date(move, date_from, date_to)
        ncf_modified = move.justech_do_ncf_modified or move.justech_do_origin_ncf or ""
        sign = -1 if move.move_type == "in_refund" else 1
        return {
            "A": line_number,
            "B": partner.justech_do_clean_vat(),
            "C": partner.justech_do_partner_id_type or "",
            "D": self._expense_type_code(move),
            "E": move.justech_do_ncf or "",
            "F": ncf_modified,
            "G": self._format_dgii_date(move.invoice_date),
            "I": self._format_dgii_date(pay_date) if pay_date else "",
            "K": self._format_amount(services) * sign,
            "L": self._format_amount(goods) * sign,
            "M": total_untaxed * sign,
            "N": itbis * sign,
            "O": self._format_amount(itbis_wh) * sign,
            "P": 0.0,
            "Q": 0.0,
            "R": 0.0,
            "S": 0.0,
            "T": isr_type,
            "U": self._format_amount(isr_wh) * sign,
            "V": 0.0,
            "W": 0.0,
            "X": 0.0,
            "Y": 0.0,
            "Z": self._payment_method_code(move),
            "AA": move.justech_do_dgii_line_status or "1",
        }

    def export_xlsx(self, company, date_from, date_to, moves=None):
        mapping = self._load_mapping()
        moves = moves or self._moves_for_period(company, date_from, date_to)
        errors = self.validate_moves_606(company, date_from, date_to, moves=moves)
        if errors:
            raise UserError("\n".join(errors))

        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_("Se requiere la librería xlsxwriter para exportar el 606."))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet_name = mapping.get("hoja_principal", "Herramienta Formato 606")[:31]
        sheet = workbook.add_worksheet(sheet_name)
        bold = workbook.add_format({"bold": True})
        amount_fmt = workbook.add_format({"num_format": "0.00"})

        period = date_from.strftime("%Y%m")
        company_vat = re.sub(r"[\s\-]", "", company.vat or "")
        sheet.write(3, 0, "RNC o Cédula")
        sheet.write(3, 1, company_vat)
        sheet.write(4, 0, "Periodo")
        sheet.write(4, 1, period)
        sheet.write(5, 0, "Cantidad Registros")
        sheet.write(5, 2, len(moves))

        header_row = mapping.get("fila_encabezado", 11) - 1
        columns = mapping.get("columnas", [])
        col_index = {}
        for col_def in columns:
            letter = col_def.get("columna_excel")
            if not letter:
                continue
            idx = self._excel_col_index(letter)
            col_index[letter] = idx
            sheet.write(header_row, idx, col_def.get("nombre_dgii", ""), bold)

        data_start = mapping.get("fila_inicio_datos", 12) - 1
        for line_no, move in enumerate(moves, start=1):
            row_vals = self.build_row_values(move, line_no, date_from, date_to)
            row = data_start + line_no - 1
            for letter, value in row_vals.items():
                idx = col_index.get(letter)
                if idx is None:
                    continue
                if letter in ("A", "C", "D", "E", "F", "G", "I", "T", "Z", "AA"):
                    sheet.write(row, idx, value)
                else:
                    sheet.write(row, idx, value, amount_fmt)

        workbook.close()
        filename = f"DGII_606_{period}.xlsx"
        return base64.b64encode(output.getvalue()), filename

    @staticmethod
    def _excel_col_index(letters):
        result = 0
        for char in letters:
            result = result * 26 + (ord(char) - 64)
        return result - 1
