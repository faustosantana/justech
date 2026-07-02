"""Exportador DGII 608 — comprobantes fiscales anulados."""
from __future__ import annotations

import re

from odoo import _, models

NCF_FULL_RE = re.compile(r"^[BE][0-9]{2}[0-9]{8}$")


class JustechDoDgii608Exporter(models.AbstractModel):
    _name = "justech.do.dgii.608.exporter"
    _inherit = "justech.do.dgii.exporter.mixin"
    _description = "Exportador DGII formato 608"

    def _dgii_report_code(self):
        return "608"

    def _dgii_mapping_filename(self):
        return "dgii_608_mapping.json"

    def _dgii_summary_title(self):
        return _("Resumen validación 608")

    def _dgii_partner_role_label(self):
        return _("Contacto")

    def _dgii_text_columns(self):
        return {"A", "C"}

    def _dgii_withholding_affects(self, catalog):
        return False

    def _dgii_is_itbis_tax(self, tax):
        return False

    def _is_cancelled_move(self, move):
        return False

    def _is_excluded_from_report(self, move):
        return bool((move.justech_do_dgii_exclusion_reason or "").strip())

    def _dgii_base_period_domain(self, company, date_from, date_to):
        return [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("justech_do_ncf_voided", "=", True),
            ("justech_do_ncf_void_date", ">=", date_from),
            ("justech_do_ncf_void_date", "<=", date_to),
        ]

    def _ncf_is_valid_format(self, ncf):
        ncf = (ncf or "").strip().upper().replace(" ", "")
        return bool(NCF_FULL_RE.match(ncf))

    def _cancel_type_code(self, move):
        code = (move.justech_do_ncf_cancel_type or "").strip()
        if not code:
            return ""
        return code.lstrip("0") or code

    def _ncf_prefix(self, move):
        doc = move.justech_do_document_type_id
        if doc and doc.prefix:
            return doc.prefix
        ncf = move.justech_do_ncf or ""
        return ncf[:3] if len(ncf) >= 3 else ncf

    def _void_user_name(self, move):
        consumption = self.env["justech.do.ncf.consumption"].search(
            [("move_id", "=", move.id), ("state", "=", "voided")],
            limit=1,
        )
        if consumption and consumption.void_user_id:
            return consumption.void_user_id.display_name
        return ""

    def _refresh_move_fiscal_state(self, move, date_from, date_to):
        if self._is_excluded_from_report(move):
            state = "excluded"
        elif self._dgii_validate_single_move(move, date_from, date_to):
            state = "incomplete"
        else:
            state = "valid"
        if move.justech_do_dgii_fiscal_state != state:
            move.justech_do_dgii_fiscal_state = state
        return state

    def _dgii_validate_single_move(self, move, date_from, date_to):
        errors = []
        label = self._move_label(move)
        if not move.justech_do_ncf_voided:
            errors.append(_("%(doc)s: el comprobante no está anulado.") % {"doc": label})
        ncf = move.justech_do_ncf
        if not ncf:
            errors.append(_("%(doc)s: falta NCF anulado.") % {"doc": label})
        elif not self._ncf_is_valid_format(ncf):
            errors.append(
                _("%(doc)s: NCF inválido «%(ncf)s».")
                % {"doc": label, "ncf": ncf}
            )
        if not move.justech_do_ncf_void_date:
            errors.append(_("%(doc)s: falta fecha de anulación.") % {"doc": label})
        elif move.justech_do_ncf_void_date < date_from or move.justech_do_ncf_void_date > date_to:
            errors.append(
                _("%(doc)s: la fecha de anulación %(fecha)s está fuera del período.")
                % {"doc": label, "fecha": move.justech_do_ncf_void_date}
            )
        if not self._cancel_type_code(move):
            errors.append(_("%(doc)s: falta tipo de anulación DGII (608).") % {"doc": label})
        if not (move.justech_do_ncf_void_reason or "").strip():
            errors.append(_("%(doc)s: falta motivo de anulación.") % {"doc": label})
        return errors

    def format_validation_summary(self, result):
        lines = super().format_validation_summary(result).split("\n")
        counts = result["counts"]
        lines.extend(
            [
                "",
                _("Resumen de anulados (documentos válidos)"),
                "—" * 24,
                _("Comprobantes exportables: %(n)s") % {"n": counts["valid"]},
                _("Documentos excluidos: %(n)s") % {"n": counts["excluded"]},
                _("Documentos incompletos: %(n)s") % {"n": counts["incomplete"]},
            ]
        )
        return "\n".join(lines)

    def _dgii_build_row_values(self, move, line_number, date_from, date_to):
        return {
            "A": move.justech_do_ncf or "",
            "B": self._format_dgii_date(move.invoice_date),
            "C": self._cancel_type_code(move),
        }

    def validate_period_608(self, company, date_from, date_to, refresh_states=True):
        return self.validate_period(company, date_from, date_to, refresh_states)
