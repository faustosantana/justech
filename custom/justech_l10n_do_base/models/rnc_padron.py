# -*- coding: utf-8 -*-
"""Padrón local RNC (solo lectura operativa; sincronización controlada)."""
from __future__ import annotations

from odoo import api, fields, models


class JustechDoRncPadron(models.Model):
    _name = "justech.do.rnc.padron"
    _description = "Padrón local RNC DGII"
    _order = "rnc"
    _rec_name = "name"

    rnc = fields.Char(string="RNC", required=True, index=True)
    name = fields.Char(string="Razón social", required=True)
    trade_name = fields.Char(string="Nombre comercial")
    state = fields.Selection(
        [
            ("active", "Activo"),
            ("inactive", "Inactivo"),
            ("unknown", "Desconocido"),
        ],
        string="Estado",
        default="active",
    )
    category = fields.Char(string="Categoría / tipo contribuyente")
    economic_activity = fields.Char(string="Actividad económica")
    source = fields.Char(string="Fuente", default="dgii_txt", required=True)
    sync_date = fields.Datetime(string="Última sincronización", index=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("justech_rnc_padron_rnc_uniq", "unique(rnc)", "El RNC ya existe en el padrón local."),
    ]

    @api.model
    def normalize_rnc(self, value):
        return self.env["justech.do.fiscal.validator.service"].normalize_vat(value)

    @api.model
    def lookup(self, rnc):
        cleaned = self.normalize_rnc(rnc)
        if not cleaned:
            return self.browse()
        return self.search([("rnc", "=", cleaned)], limit=1)

    @api.model
    def last_sync_info(self):
        last = self.search([], order="sync_date desc, id desc", limit=1)
        return {
            "count": self.search_count([]),
            "sync_date": last.sync_date if last else False,
            "source": last.source if last else False,
        }
