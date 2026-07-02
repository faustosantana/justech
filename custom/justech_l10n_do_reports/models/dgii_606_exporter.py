"""Exportador piloto DGII 606 — layout oficial según dgii_606_mapping.json."""
from __future__ import annotations

from odoo import _, models


class JustechDoDgii606Exporter(models.AbstractModel):
    _name = "justech.do.dgii.606.exporter"
    _inherit = "justech.do.dgii.exporter.mixin"
    _description = "Exportador DGII formato 606"

    def _dgii_report_code(self):
        return "606"

    def _dgii_mapping_filename(self):
        return "dgii_606_mapping.json"

    def _dgii_summary_title(self):
        return _("Resumen validación 606")

    def _dgii_partner_role_label(self):
        return _("Proveedor")

    def _dgii_text_columns(self):
        return {"A", "C", "D", "E", "F", "G", "I", "T", "Z", "AA"}

    def _dgii_withholding_affects(self, catalog):
        return catalog.affects_606

    def _dgii_is_itbis_tax(self, tax):
        if not tax:
            return False
        name = (tax.name or "").upper()
        return "ITBIS" in name or (
            tax.amount in (18.0, 16.0, 9.0, 8.0) and tax.type_tax_use == "purchase"
        )

    def _dgii_base_period_domain(self, company, date_from, date_to):
        return [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("move_type", "in", ("in_invoice", "in_refund")),
            ("invoice_date", ">=", date_from),
            ("invoice_date", "<=", date_to),
        ]

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
        doc = move.justech_do_document_type_id
        if doc and doc.prefix == "B13":
            return "06"
        return "02"

    def _dgii_validate_single_move(self, move, date_from, date_to):
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
            lambda l: not self._dgii_is_itbis_tax(l.tax_line_id)
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

    def _dgii_build_row_values(self, move, line_number, date_from, date_to):
        partner = move.partner_id
        services, goods = self._split_goods_services(move)
        itbis = self._format_amount(
            self.env["justech.do.fiscal.report"]._move_itbis_amount(move)
        )
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

    # Alias retrocompatibles
    def classify_moves_606(self, company, date_from, date_to, refresh_states=True):
        return self.classify_moves(company, date_from, date_to, refresh_states)

    def validate_period_606(self, company, date_from, date_to, refresh_states=True):
        return self.validate_period(company, date_from, date_to, refresh_states)

    def validate_moves_606(self, company, date_from, date_to, moves=None):
        return self.validate_moves(company, date_from, date_to, moves=moves)

    def _validate_single_move(self, move, date_from, date_to):
        return self._dgii_validate_single_move(move, date_from, date_to)

    def build_row_values(self, move, line_number, date_from, date_to):
        return self._dgii_build_row_values(move, line_number, date_from, date_to)
