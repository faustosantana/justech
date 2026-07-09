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

    def _is_cancelled_move(self, move):
        return False

    def _is_excluded_from_report(self, move):
        return bool((move.justech_do_dgii_exclusion_reason or "").strip())

    def _dgii_base_period_domain(self, company, date_from, date_to):
        domain = [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
        ]
        Move = self.env["account.move"]
        if "justech_do_ncf_voided" in Move._fields and "l10n_do_cancellation_type" in Move._fields:
            domain.extend(
                [
                    "|",
                    ("justech_do_ncf_voided", "=", True),
                    ("l10n_do_cancellation_type", "!=", False),
                ]
            )
        elif "justech_do_ncf_voided" in Move._fields:
            domain.append(("justech_do_ncf_voided", "=", True))
        elif "l10n_do_cancellation_type" in Move._fields:
            domain.append(("l10n_do_cancellation_type", "!=", False))
        return domain

    def classify_moves(self, company, date_from, date_to, refresh_states=True):
        all_moves = self.env["account.move"].search(
            self._dgii_base_period_domain(company, date_from, date_to),
            order="invoice_date, id",
        )
        fdp = self._fdp()
        period_moves = all_moves.filtered(
            lambda m: fdp.is_voided(m)
            and (void_date := fdp.get_void_date(m))
            and date_from <= void_date <= date_to
        )
        buckets = {
            "all": period_moves,
            "cancelled": self.env["account.move"],
            "excluded": self.env["account.move"],
            "incomplete": self.env["account.move"],
            "valid": self.env["account.move"],
        }
        for move in period_moves:
            if refresh_states:
                state = self._refresh_move_fiscal_state(move, date_from, date_to)
            elif self._is_excluded_from_report(move):
                state = "excluded"
            elif self._dgii_validate_single_move(move, date_from, date_to):
                state = "incomplete"
            else:
                state = "valid"
            buckets[state] |= move
        return buckets

    def _ncf_is_valid_format(self, ncf):
        ncf = (ncf or "").strip().upper().replace(" ", "")
        return bool(NCF_FULL_RE.match(ncf))

    def _cancel_type_code(self, move):
        return self._fdp().get_cancellation_type(move)

    def _ncf_prefix(self, move):
        return self._fdp().get_document_type_prefix(move)

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
        fdp = self._fdp()
        if not fdp.is_voided(move):
            errors.append(_("%(doc)s: el comprobante no está anulado.") % {"doc": label})
        ncf = fdp.get_ncf(move)
        if not ncf:
            errors.append(_("%(doc)s: falta NCF anulado.") % {"doc": label})
        elif not self._ncf_is_valid_format(ncf):
            errors.append(
                _("%(doc)s: NCF inválido «%(ncf)s».")
                % {"doc": label, "ncf": ncf}
            )
        void_date = fdp.get_void_date(move)
        if not void_date:
            errors.append(_("%(doc)s: falta fecha de anulación.") % {"doc": label})
        elif void_date < date_from or void_date > date_to:
            errors.append(
                _("%(doc)s: la fecha de anulación %(fecha)s está fuera del período.")
                % {"doc": label, "fecha": void_date}
            )
        if not self._cancel_type_code(move):
            errors.append(_("%(doc)s: falta tipo de anulación DGII (608).") % {"doc": label})
        if not fdp.get_void_reason(move) and not fdp.get_cancellation_type(move):
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
        fdp = self._fdp()
        return {
            "A": fdp.get_ncf(move),
            "B": self._format_dgii_date(move.invoice_date),
            "C": self._cancel_type_code(move),
        }

    def validate_period_608(self, company, date_from, date_to, refresh_states=True):
        return self.validate_period(company, date_from, date_to, refresh_states)
