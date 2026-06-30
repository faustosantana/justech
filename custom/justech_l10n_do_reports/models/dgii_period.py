# -*- coding: utf-8 -*-
"""Utilidades de período fiscal DGII (YYYYMM)."""
from __future__ import annotations

import calendar
import re
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_PERIOD_RE = re.compile(r"^\d{6}$")


class JustechDoDgiiPeriod(models.AbstractModel):
    _name = "justech.do.dgii.period"
    _description = "Utilidades período fiscal DGII"

    @api.model
    def default_period_code(self, reference_date=None):
        ref = reference_date or fields.Date.context_today(self)
        ref = fields.Date.to_date(ref)
        return ref.strftime("%Y%m")

    @api.model
    def period_bounds_from_code(self, period_code):
        """Convierte YYYYMM en (primer día, último día) del mes."""
        code = (period_code or "").strip()
        if not _PERIOD_RE.match(code):
            raise UserError(
                _("Período inválido «%(p)s». Use formato YYYYMM, por ejemplo 202606.")
                % {"p": period_code or ""}
            )
        year = int(code[:4])
        month = int(code[4:6])
        if month < 1 or month > 12:
            raise UserError(
                _("Mes inválido en período %(p)s. Debe estar entre 01 y 12.")
                % {"p": code}
            )
        if year < 2000 or year > 2100:
            raise UserError(
                _("Año inválido en período %(p)s.") % {"p": code}
            )
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)

    @api.model
    def period_code_from_dates(self, date_from, date_to):
        """Deriva YYYYMM desde la fecha inicial del período."""
        date_from = fields.Date.to_date(date_from)
        if not date_from:
            return False
        return date_from.strftime("%Y%m")

    @api.model
    def validate_period_dates(self, date_from, date_to, period_code=None):
        """Valida coherencia entre fechas y período YYYYMM."""
        date_from = fields.Date.to_date(date_from)
        date_to = fields.Date.to_date(date_to)
        if not date_from or not date_to:
            raise UserError(_("Debe indicar fecha desde y fecha hasta."))
        if date_from > date_to:
            raise UserError(_("La fecha desde no puede ser posterior a la fecha hasta."))
        if period_code:
            expected_from, expected_to = self.period_bounds_from_code(period_code)
            if date_from != expected_from or date_to != expected_to:
                raise UserError(
                    _(
                        "Las fechas %(desde)s — %(hasta)s no coinciden con el período %(periodo)s "
                        "(esperado: %(exp_desde)s — %(exp_hasta)s)."
                    )
                    % {
                        "desde": date_from,
                        "hasta": date_to,
                        "periodo": period_code,
                        "exp_desde": expected_from,
                        "exp_hasta": expected_to,
                    }
                )
        return date_from, date_to
