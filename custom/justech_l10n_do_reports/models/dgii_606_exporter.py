"""Exportador piloto DGII 606 — layout oficial según dgii_606_mapping.json."""
from __future__ import annotations

import base64
import io
import json
import re
from collections import defaultdict
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

    def _base_period_domain(self, company, date_from, date_to):
        return [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("move_type", "in", ("in_invoice", "in_refund")),
            ("invoice_date", ">=", date_from),
            ("invoice_date", "<=", date_to),
        ]

    def _is_cancelled_move(self, move):
        return bool(move.justech_do_ncf_voided or move.justech_do_dgii_line_status == "2")

    def _move_label(self, move):
        return move.name or move.ref or str(move.id)

    def _validate_single_move(self, move, date_from, date_to):
        """Errores bloqueantes para un documento incluido en DGII."""
        errors = []
        label = self._move_label(move)
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
        _itbis_wh, _isr_wh, _isr_type, missing_codes = self._withholding_breakdown(move)
        for wh_name in missing_codes:
            errors.append(
                _("%(doc)s: retención «%(wh)s» sin código DGII configurado.")
                % {"doc": label, "wh": wh_name}
            )
        return errors

    def _refresh_move_fiscal_state(self, move, date_from, date_to):
        if self._is_cancelled_move(move):
            state = "cancelled"
        elif not move.justech_do_include_in_dgii:
            state = "excluded"
        elif self._validate_single_move(move, date_from, date_to):
            state = "incomplete"
        else:
            state = "valid"
        if move.justech_do_dgii_fiscal_state != state:
            move.justech_do_dgii_fiscal_state = state
        return state

    def classify_moves_606(self, company, date_from, date_to, refresh_states=True):
        """Clasifica compras del período para exportación DGII."""
        all_moves = self.env["account.move"].search(
            self._base_period_domain(company, date_from, date_to),
            order="invoice_date, id",
        )
        buckets = {
            "all": all_moves,
            "cancelled": self.env["account.move"],
            "excluded": self.env["account.move"],
            "incomplete": self.env["account.move"],
            "valid": self.env["account.move"],
        }
        for move in all_moves:
            if refresh_states:
                state = self._refresh_move_fiscal_state(move, date_from, date_to)
            elif self._is_cancelled_move(move):
                state = "cancelled"
            elif not move.justech_do_include_in_dgii:
                state = "excluded"
            elif self._validate_single_move(move, date_from, date_to):
                state = "incomplete"
            else:
                state = "valid"
            buckets[state] |= move
        return buckets

    def validate_period_606(self, company, date_from, date_to, refresh_states=True):
        """Validación estructurada del período con resumen agrupado."""
        buckets = self.classify_moves_606(
            company, date_from, date_to, refresh_states=refresh_states
        )
        errors_flat = []
        errors_by_partner = defaultdict(list)
        move_errors = {}

        for move in buckets["incomplete"]:
            move_errs = self._validate_single_move(move, date_from, date_to)
            move_errors[move.id] = move_errs
            partner_name = move.partner_id.display_name
            for err in move_errs:
                errors_flat.append(err)
                errors_by_partner[partner_name].append(
                    {
                        "move": self._move_label(move),
                        "move_id": move.id,
                        "error": err,
                    }
                )

        return {
            "buckets": buckets,
            "errors_flat": errors_flat,
            "errors_by_partner": dict(errors_by_partner),
            "move_errors": move_errors,
            "counts": {
                "all": len(buckets["all"]),
                "valid": len(buckets["valid"]),
                "incomplete": len(buckets["incomplete"]),
                "excluded": len(buckets["excluded"]),
                "cancelled": len(buckets["cancelled"]),
                "partners_affected": len(errors_by_partner),
                "error_lines": len(errors_flat),
            },
        }

    def format_validation_summary(self, result):
        """Resumen legible en español para wizard / historial."""
        counts = result["counts"]
        lines = [
            _("Resumen validación 606"),
            "—" * 24,
            _("Documentos en período: %(n)s") % {"n": counts["all"]},
            _("Válidos para exportar: %(n)s") % {"n": counts["valid"]},
            _("Incompletos (con errores): %(n)s") % {"n": counts["incomplete"]},
            _("Excluidos fiscalmente: %(n)s") % {"n": counts["excluded"]},
            _("Anulados: %(n)s") % {"n": counts["cancelled"]},
            _("Proveedores con errores: %(n)s") % {"n": counts["partners_affected"]},
            _("Total líneas de error: %(n)s") % {"n": counts["error_lines"]},
        ]
        if result["errors_by_partner"]:
            lines.append("")
            lines.append(_("Detalle por proveedor (primeros 15):"))
            for partner_name in list(result["errors_by_partner"])[:15]:
                partner_errors = result["errors_by_partner"][partner_name]
                move_names = sorted({item["move"] for item in partner_errors})
                lines.append(
                    _("• %(partner)s — %(moves)s factura(s), %(errs)s error(es)")
                    % {
                        "partner": partner_name,
                        "moves": len(move_names),
                        "errs": len(partner_errors),
                    }
                )
            if len(result["errors_by_partner"]) > 15:
                lines.append(
                    _("… y %(n)s proveedor(es) más. Descargue el detalle en Excel.")
                    % {"n": len(result["errors_by_partner"]) - 15}
                )
        elif counts["valid"]:
            lines.append("")
            lines.append(_("Sin errores en documentos incluidos. Listo para exportar."))
        return "\n".join(lines)

    def validate_moves_606(self, company, date_from, date_to, moves=None):
        """API retrocompatible: errores planos de documentos incluidos."""
        if moves is not None:
            errors = []
            for move in moves:
                if not move.justech_do_include_in_dgii or self._is_cancelled_move(move):
                    continue
                errors.extend(self._validate_single_move(move, date_from, date_to))
            return errors
        result = self.validate_period_606(company, date_from, date_to)
        return result["errors_flat"]

    def _moves_for_period(self, company, date_from, date_to, only_valid=True):
        buckets = self.classify_moves_606(company, date_from, date_to)
        if only_valid:
            return buckets["valid"]
        return buckets["all"].filtered(
            lambda m: m.justech_do_include_in_dgii and not self._is_cancelled_move(m)
        )

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

    def export_errors_xlsx(self, company, date_from, date_to, result=None):
        """Excel con detalle de errores e inclusiones/exclusiones."""
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_("Se requiere la librería xlsxwriter para exportar errores."))

        result = result or self.validate_period_606(company, date_from, date_to)
        buckets = result["buckets"]
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        bold = workbook.add_format({"bold": True})
        wrap = workbook.add_format({"text_wrap": True})

        sheet_errors = workbook.add_worksheet("Errores"[:31])
        headers = [
            _("Proveedor"),
            _("RNC/Cédula"),
            _("Factura"),
            _("NCF"),
            _("Estado fiscal"),
            _("Errores"),
        ]
        for col, header in enumerate(headers):
            sheet_errors.write(0, col, header, bold)
        row = 1
        state_labels = dict(
            self.env["account.move"]._fields["justech_do_dgii_fiscal_state"].selection
        )
        for move in buckets["incomplete"]:
            errs = result["move_errors"].get(move.id) or self._validate_single_move(
                move, date_from, date_to
            )
            sheet_errors.write(row, 0, move.partner_id.display_name)
            sheet_errors.write(row, 1, move.partner_id.vat or "")
            sheet_errors.write(row, 2, self._move_label(move))
            sheet_errors.write(row, 3, move.justech_do_ncf or "")
            sheet_errors.write(row, 4, state_labels.get(move.justech_do_dgii_fiscal_state, ""))
            sheet_errors.write(row, 5, "\n".join(errs), wrap)
            row += 1

        sheet_excluded = workbook.add_worksheet("Excluidos"[:31])
        ex_headers = [
            _("Proveedor"),
            _("Factura"),
            _("NCF"),
            _("Estado fiscal"),
            _("Motivo exclusión"),
        ]
        for col, header in enumerate(ex_headers):
            sheet_excluded.write(0, col, header, bold)
        for row_idx, move in enumerate(buckets["excluded"] | buckets["cancelled"], start=1):
            sheet_excluded.write(row_idx, 0, move.partner_id.display_name)
            sheet_excluded.write(row_idx, 1, self._move_label(move))
            sheet_excluded.write(row_idx, 2, move.justech_do_ncf or "")
            sheet_excluded.write(
                row_idx, 3, state_labels.get(move.justech_do_dgii_fiscal_state, "")
            )
            sheet_excluded.write(row_idx, 4, move.justech_do_dgii_exclusion_reason or "")

        sheet_valid = workbook.add_worksheet("Validos"[:31])
        val_headers = [_("Proveedor"), _("Factura"), _("NCF"), _("Fecha"), _("Total")]
        for col, header in enumerate(val_headers):
            sheet_valid.write(0, col, header, bold)
        for row_idx, move in enumerate(buckets["valid"], start=1):
            sheet_valid.write(row_idx, 0, move.partner_id.display_name)
            sheet_valid.write(row_idx, 1, self._move_label(move))
            sheet_valid.write(row_idx, 2, move.justech_do_ncf or "")
            sheet_valid.write(row_idx, 3, str(move.invoice_date or ""))
            sheet_valid.write(row_idx, 4, abs(move.amount_total_signed))

        workbook.close()
        period = date_from.strftime("%Y%m")
        filename = f"DGII_606_errores_{period}.xlsx"
        return base64.b64encode(output.getvalue()), filename

    def export_xlsx(self, company, date_from, date_to, moves=None, strict=False):
        """Exporta 606. Por defecto solo documentos fiscalmente válidos."""
        mapping = self._load_mapping()
        if moves is None:
            result = self.validate_period_606(company, date_from, date_to)
            moves = result["buckets"]["valid"]
            if strict and result["counts"]["incomplete"]:
                raise UserError(
                    self.format_validation_summary(result)
                    + "\n\n"
                    + _("Corrija los documentos incompletos o exclúyalos fiscalmente.")
                )
        else:
            errors = self.validate_moves_606(company, date_from, date_to, moves=moves)
            if errors:
                raise UserError("\n".join(errors))

        if not moves:
            raise UserError(
                _("No hay documentos fiscalmente válidos para exportar en el período seleccionado.")
            )

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
