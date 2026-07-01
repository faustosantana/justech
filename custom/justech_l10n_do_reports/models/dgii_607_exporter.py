"""Exportador piloto DGII 607 — layout oficial según dgii_607_mapping.json."""
from __future__ import annotations

import re

from odoo import _, models

NCF_FULL_RE = re.compile(r"^[BE][0-9]{2}[0-9]{8}$")


class JustechDoDgii607Exporter(models.AbstractModel):
    _name = "justech.do.dgii.607.exporter"
    _inherit = "justech.do.dgii.exporter.mixin"
    _description = "Exportador DGII formato 607"

    CONSUMER_NCF_PREFIXES = ("B02", "B12", "E32", "E33")

    def _dgii_report_code(self):
        return "607"

    def _dgii_mapping_filename(self):
        return "dgii_607_mapping.json"

    def _dgii_summary_title(self):
        return _("Resumen validación 607")

    def _dgii_partner_role_label(self):
        return _("Cliente")

    def _dgii_text_columns(self):
        return {"A", "B", "C", "D", "E", "F", "G", "H"}

    def _dgii_withholding_affects(self, catalog):
        return catalog.affects_607

    def _dgii_is_itbis_tax(self, tax):
        if not tax:
            return False
        name = (tax.name or "").upper()
        return "ITBIS" in name or (
            tax.amount in (18.0, 16.0, 9.0, 8.0) and tax.type_tax_use == "sale"
        )

    def _dgii_base_period_domain(self, company, date_from, date_to):
        return [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("move_type", "in", ("out_invoice", "out_refund")),
            ("justech_do_ncf_voided", "=", False),
            ("invoice_date", ">=", date_from),
            ("invoice_date", "<=", date_to),
        ]

    def _ncf_prefix(self, move):
        doc = move.justech_do_document_type_id
        if doc and doc.prefix:
            return doc.prefix
        ncf = move.justech_do_ncf or ""
        return ncf[:3] if len(ncf) >= 3 else ncf

    def _is_consumer_invoice(self, move):
        return self._ncf_prefix(move) in self.CONSUMER_NCF_PREFIXES

    def _retention_date(self, move, date_from, date_to):
        for line in move.line_ids.filtered(self._is_withholding_tax_line):
            line_date = line.date
            if line_date and date_from <= line_date <= date_to:
                return line_date
        return False

    def _payment_method_code(self, move):
        if move.move_type == "out_refund":
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

    def _income_type_code(self, move):
        explicit = getattr(move, "justech_do_income_type_607", False)
        if explicit:
            return explicit
        prefix = self._ncf_prefix(move)
        if prefix in ("B14", "E44"):
            return "02"
        if prefix in self.CONSUMER_NCF_PREFIXES:
            return "01"
        return "01"

    def _ncf_is_valid_format(self, ncf):
        ncf = (ncf or "").strip().upper().replace(" ", "")
        return bool(NCF_FULL_RE.match(ncf))

    def _sales_metrics(self, buckets):
        fiscal_report = self.env["justech.do.fiscal.report"]
        exportable = buckets["valid"]
        invoices = exportable.filtered(lambda m: m.move_type == "out_invoice")
        credit_notes = exportable.filtered(lambda m: m.move_type == "out_refund")
        itbis_total = 0.0
        taxed_sales = 0.0
        exempt_sales = 0.0
        for move in exportable:
            itbis = fiscal_report._move_itbis_amount(move)
            untaxed = abs(move.amount_untaxed_signed)
            itbis_total += itbis
            if itbis > 0:
                taxed_sales += untaxed
            else:
                exempt_sales += untaxed
        return {
            "invoices": len(invoices),
            "credit_notes": len(credit_notes),
            "itbis_billed": itbis_total,
            "taxed_sales": taxed_sales,
            "exempt_sales": exempt_sales,
        }

    def _payment_amount_columns(self, move, total_with_tax, sign):
        """Asigna el total con ITBIS a la columna de medio de pago inferida."""
        cols = {letter: 0.0 for letter in ("R", "S", "T", "U", "V", "W")}
        code = self._payment_method_code(move)
        mapping = {
            "01": "R",
            "02": "S",
            "03": "T",
            "04": "U",
            "06": "U",
            "07": "R",
        }
        letter = mapping.get(code, "R")
        cols[letter] = total_with_tax * sign
        return cols

    def _dgii_validate_single_move(self, move, date_from, date_to):
        errors = []
        label = self._move_label(move)
        partner = move.partner_id
        consumer = self._is_consumer_invoice(move)
        ncf = move.justech_do_ncf
        if not ncf:
            errors.append(_("%(doc)s: falta NCF.") % {"doc": label})
        elif not self._ncf_is_valid_format(ncf):
            errors.append(
                _("%(doc)s: NCF inválido «%(ncf)s» (formato esperado: 11 caracteres, ej. B0100000001).")
                % {"doc": label, "ncf": ncf}
            )
        if move.move_type == "out_refund":
            ncf_modified = move.justech_do_ncf_modified or move.justech_do_origin_ncf
            if not ncf_modified:
                errors.append(
                    _("%(doc)s: la nota de crédito no tiene NCF modificado.")
                    % {"doc": label}
                )
            elif not self._ncf_is_valid_format(ncf_modified):
                errors.append(
                    _("%(doc)s: NCF modificado inválido «%(ncf)s».")
                    % {"doc": label, "ncf": ncf_modified}
                )
        if not consumer and not partner.vat:
            errors.append(
                _("%(doc)s: el cliente %(partner)s no tiene RNC/Cédula.")
                % {"doc": label, "partner": partner.display_name}
            )
        if partner.vat and not partner.justech_do_partner_id_type:
            errors.append(
                _("%(doc)s: el cliente %(partner)s no tiene tipo de identificación DGII.")
                % {"doc": label, "partner": partner.display_name}
            )
        if not self._income_type_code(move):
            errors.append(_("%(doc)s: falta tipo de ingreso DGII.") % {"doc": label})
        if move.invoice_date and (move.invoice_date < date_from or move.invoice_date > date_to):
            errors.append(
                _("%(doc)s: la fecha %(fecha)s está fuera del período.")
                % {"doc": label, "fecha": move.invoice_date}
            )
        positive_taxes = move.line_ids.filtered(
            lambda l: l.tax_line_id and l.tax_line_id.amount > 0
        )
        unknown = positive_taxes.filtered(
            lambda l: not self._dgii_is_itbis_tax(l.tax_line_id)
            and "ISC" not in (l.tax_line_id.name or "").upper()
            and l.tax_line_id.type_tax_use == "sale"
        )
        if unknown:
            errors.append(
                _("%(doc)s: impuesto no clasificado para DGII: %(taxes)s")
                % {
                    "doc": label,
                    "taxes": ", ".join(unknown.mapped("tax_line_id.name")),
                }
            )
        itbis_wh, isr_wh, _isr_type, missing_codes = self._withholding_breakdown(move)
        for wh_name in missing_codes:
            errors.append(
                _("%(doc)s: retención «%(wh)s» sin código DGII configurado.")
                % {"doc": label, "wh": wh_name}
            )
        if (itbis_wh or isr_wh) and not self._retention_date(move, date_from, date_to):
            errors.append(
                _("%(doc)s: falta fecha de retención en el período reportado.")
                % {"doc": label}
            )
        return errors

    def format_validation_summary(self, result):
        lines = super().format_validation_summary(result).split("\n")
        metrics = self._sales_metrics(result["buckets"])
        counts = result["counts"]
        lines.extend(
            [
                "",
                _("Resumen de ventas (documentos válidos)"),
                "—" * 24,
                _("Facturas exportables: %(n)s") % {"n": metrics["invoices"]},
                _("Notas de crédito: %(n)s") % {"n": metrics["credit_notes"]},
                _("ITBIS facturado: %(amount).2f") % {"amount": metrics["itbis_billed"]},
                _("Ventas gravadas: %(amount).2f") % {"amount": metrics["taxed_sales"]},
                _("Ventas exentas: %(amount).2f") % {"amount": metrics["exempt_sales"]},
                "",
                _("Documentos excluidos: %(n)s") % {"n": counts["excluded"]},
                _("Documentos incompletos: %(n)s") % {"n": counts["incomplete"]},
            ]
        )
        return "\n".join(lines)

    def _dgii_build_row_values(self, move, line_number, date_from, date_to):
        partner = move.partner_id
        itbis = self._format_amount(
            self.env["justech.do.fiscal.report"]._move_itbis_amount(move)
        )
        itbis_wh, isr_wh, _isr_type, _missing = self._withholding_breakdown(move)
        total_untaxed = self._format_amount(move.amount_untaxed_signed)
        total_with_tax = self._format_amount(move.amount_total_signed)
        retention_date = self._retention_date(move, date_from, date_to)
        ncf_modified = move.justech_do_ncf_modified or move.justech_do_origin_ncf or ""
        sign = -1 if move.move_type == "out_refund" else 1
        payment_cols = self._payment_amount_columns(move, total_with_tax, sign)
        vat = ""
        if partner.vat:
            vat = (
                partner.justech_do_clean_vat()
                if hasattr(partner, "justech_do_clean_vat")
                else partner.vat
            )
        row = {
            "A": line_number,
            "B": vat,
            "C": partner.justech_do_partner_id_type or "",
            "D": move.justech_do_ncf or "",
            "E": ncf_modified,
            "F": self._income_type_code(move),
            "G": self._format_dgii_date(move.invoice_date),
            "H": self._format_dgii_date(retention_date) if retention_date else "",
            "I": total_untaxed * sign,
            "J": itbis * sign,
            "K": self._format_amount(itbis_wh) * sign,
            "L": 0.0,
            "M": self._format_amount(isr_wh) * sign,
            "N": 0.0,
            "O": 0.0,
            "P": 0.0,
            "Q": 0.0,
        }
        row.update(payment_cols)
        return row

    def validate_period_607(self, company, date_from, date_to, refresh_states=True):
        return self.validate_period(company, date_from, date_to, refresh_states)

    def validate_moves_607(self, company, date_from, date_to, moves=None):
        return self.validate_moves(company, date_from, date_to, moves=moves)

    def _validate_single_move(self, move, date_from, date_to):
        return self._dgii_validate_single_move(move, date_from, date_to)

    def build_row_values(self, move, line_number, date_from, date_to):
        return self._dgii_build_row_values(move, line_number, date_from, date_to)
